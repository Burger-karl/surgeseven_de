from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView, View, DetailView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation
from .forms import TruckForm, BookingForm, TruckActivationForm, TruckDeactivationForm, TruckApprovalForm, TruckImageForm, AdminBookingForm, TruckEditForm
from .models import Truck, Booking, TruckImage
from subscriptions.models import UserSubscription, SubscriptionPlan
from users.models import ReferralBonus, Referral, User
from payment.models import Payment
from django.db.models import F
from django.db import transaction, models
from django.contrib.messages.views import SuccessMessageMixin


# Create your views here.

# Decorator to check if user is logged in and has the required user type
def user_type_required(user_type):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.user_type != user_type:
                raise PermissionDenied(f"Only {user_type}s can access this view.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# Decorator to ensure user is superuser/admin
def admin_required(view_func):
    decorated_view_func = login_required(user_passes_test(lambda u: u.is_superuser)(view_func))
    return decorated_view_func


@method_decorator([login_required, user_type_required('truck_owner')], name='dispatch')
class TruckCreateView(CreateView):
    model = Truck
    form_class = TruckForm
    template_name = 'booking/truck_form.html'
    success_url = reverse_lazy('truck_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_form'] = TruckImageForm(self.request.POST, self.request.FILES)
        else:
            context['image_form'] = TruckImageForm()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_form = context['image_form']
        
        if form.is_valid() and image_form.is_valid():
            truck = form.save(commit=False)
            truck.owner = self.request.user
            truck.save()

            # Save exactly 3 images
            images = self.request.FILES.getlist('images')
            for image in images:
                TruckImage.objects.create(truck=truck, image=image)

            messages.success(self.request, "Truck created successfully with 3 images!")
            return super().form_valid(form)
        else:
            return self.form_invalid(form)     
           


# Truck List View
# @method_decorator(login_required, name='dispatch')
# class TruckListView(ListView):
#     model = Truck
#     template_name = 'booking/truck_list.html'
#     context_object_name = 'trucks'

#     def get_queryset(self):
#         if self.request.user.user_type == 'truck_owner':
#             return Truck.objects.filter(owner=self.request.user)
#         return Truck.objects.filter(available=True)


@method_decorator(login_required, name='dispatch')
class TruckListView(ListView):
    model = Truck
    template_name = 'booking/truck_list.html'
    context_object_name = 'trucks'

    def get_queryset(self):
        if self.request.user.user_type == 'truck_owner':
            return Truck.objects.filter(owner=self.request.user)
        return Truck.objects.filter(available=True, activated=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.user_type == 'truck_owner':
            # Add activation status for owner's trucks
            trucks = context['trucks']
            for truck in trucks:
                truck.needs_activation = not truck.activated
                truck.has_pending_payment = Payment.objects.filter(
                    truck=truck,
                    payment_type=Payment.TRUCK_ACTIVATION,
                    verified=False
                ).exists()
        return context


# Booking Create View
@method_decorator([login_required, user_type_required('client')], name='dispatch')
class BookingCreateView(CreateView):
    model = Booking
    form_class = BookingForm
    template_name = 'booking/booking_form.html'
    success_url = reverse_lazy('booking_list')

    def get_initial(self):
        initial = super().get_initial()
        truck_id = self.kwargs.get('truck_id')
        if truck_id:
            initial['truck'] = get_object_or_404(Truck, id=truck_id)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        truck_id = self.kwargs.get('truck_id')
        if truck_id:
            truck = get_object_or_404(Truck, id=truck_id)
            # Fetch the first image of the truck
            first_image = truck.images.first()  # Access related images using the related_name
            context['truck'] = truck
            context['truck_image'] = first_image.image if first_image else None  # Pass the image to the template
        return context

    def form_valid(self, form):
        user = self.request.user
        
        if user.user_type != 'client':
            raise PermissionDenied("Only clients can book trucks.")

        active_subscription = UserSubscription.objects.filter(
            user=user,
            subscription_status='active',
            is_active=True
        ).exclude(plan__name=SubscriptionPlan.FREE).first()

        if not active_subscription:
            raise PermissionDenied("You must have an active paid subscription to book a truck.")

        # Calculate insurance payment as 1% of product value for premium users
        if active_subscription.plan.name == SubscriptionPlan.PREMIUM:
            insurance_payment = float(form.cleaned_data['product_value']) * 0.01
        else:
            insurance_payment = 0

        booking = form.save(commit=False)
        booking.client = user
        booking.truck = get_object_or_404(Truck, id=self.kwargs.get('truck_id'))
        booking.insurance_payment = insurance_payment

        # Calculate total delivery cost
        booking.total_delivery_cost = booking.delivery_cost + insurance_payment
        booking.save()

        return redirect('booking_list')
    


@method_decorator(login_required, name='dispatch')
class BookingListView(ListView):
    model = Booking
    template_name = 'booking/booking_list.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'client':
            return Booking.objects.filter(client=user, payment_completed=False)
        elif user.user_type == 'truck_owner':
            return Booking.objects.filter(truck__owner=user, payment_completed=False)
        return Booking.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = True  # Add flag to indicate editing is allowed
        return context


@method_decorator([login_required, user_type_required('client')], name='dispatch')
class BookingUpdateView(UpdateView):
    model = Booking
    form_class = BookingForm
    template_name = 'booking/booking_form.html'
    success_url = reverse_lazy('booking_list')

    def get_queryset(self):
        # Only allow editing of unpaid bookings owned by the current user
        return Booking.objects.filter(
            client=self.request.user,
            payment_completed=False
        )

    def form_valid(self, form):
        booking = form.save(commit=False)
        
        # Recalculate insurance payment if needed
        active_subscription = UserSubscription.objects.filter(
            user=self.request.user,
            subscription_status='active',
            is_active=True
        ).exclude(plan__name=SubscriptionPlan.FREE).first()

        if active_subscription and active_subscription.plan.name == SubscriptionPlan.PREMIUM:
            booking.insurance_payment = float(form.cleaned_data['product_value']) * 0.01
        else:
            booking.insurance_payment = 0

        booking.total_delivery_cost = booking.delivery_cost + booking.insurance_payment
        booking.save()
        return redirect(self.success_url)
    


from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import resend
from django.conf import settings
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

# Configure Resend
resend.api_key = settings.RESEND_API_KEY

@method_decorator(login_required, name='dispatch')
class GenerateReceiptView(DetailView):
    model = Booking
    template_name = 'booking/receipt.html'
    context_object_name = 'booking'
    slug_field = 'booking_code'
    slug_url_kwarg = 'booking_code'

    def get_object(self, queryset=None):
        booking_code = self.kwargs.get('booking_code')
        booking = get_object_or_404(Booking, booking_code=booking_code)
        
        if booking.client != self.request.user:
            raise PermissionDenied("You do not have permission to view this receipt.")
        
        return booking

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.object
        
        # Add all required data to context
        context['truck_name'] = booking.truck.name
        context['product_name'] = booking.product_name
        context['product_weight_display'] = booking.get_product_weight_display()
        context['pickup_state_display'] = booking.get_pickup_state_display()
        context['destination_state_display'] = booking.get_destination_state_display()
        context['booking_status_display'] = booking.get_booking_status_display()
        context['delivery_cost'] = booking.delivery_cost
        context['insurance_payment'] = booking.insurance_payment
        context['total_delivery_cost'] = booking.total_delivery_cost
        
        # Premium subscription check
        context['has_premium'] = UserSubscription.objects.filter(
            user=booking.client,
            subscription_status='active',
            is_active=True,
            plan__name=SubscriptionPlan.PREMIUM
        ).exists()
        
        context['insurance_company'] = "AXA Mansard Insurance"
        context['current_year'] = timezone.now().year
        context['site_url'] = settings.SITE_URL
        return context

    def render_to_response(self, context, **response_kwargs):
        booking = context['booking']
        
        # Generate and send email with receipts using Resend
        if booking.client.email:
            self.send_receipt_email(booking, context)
        
        return super().render_to_response(context, **response_kwargs)

    def send_receipt_email(self, booking, context):
        try:
            # Render booking receipt
            booking_receipt_html = render_to_string('booking/emails/booking_receipt.html', context)
            booking_receipt_text = strip_tags(booking_receipt_html)
            
            # Prepare email content
            subject = f"Booking Confirmation - #{booking.booking_code}"
            
            # Create email parameters for Resend
            params = {
                "from": f"SurgeSeven <{settings.DEFAULT_FROM_EMAIL}>",
                "to": [booking.client.email],
                "subject": subject,
                "html": booking_receipt_html,
                "text": booking_receipt_text,
            }
            
            # Send email using Resend
            response = resend.Emails.send(params)
            logger.info(f"Booking receipt email sent to {booking.client.email}. Resend ID: {response['id']}")
            
        except Exception as e:
            logger.error(f"Error sending booking receipt email: {str(e)}")


@method_decorator(login_required, name='dispatch')
class InsuranceReceiptView(DetailView):
    model = Booking
    template_name = 'booking/insurance_receipt.html'
    context_object_name = 'booking'
    slug_field = 'booking_code'
    slug_url_kwarg = 'booking_code'

    def get_object(self, queryset=None):
        booking_code = self.kwargs.get('booking_code')
        booking = get_object_or_404(Booking, booking_code=booking_code)
        
        if booking.client != self.request.user:
            raise PermissionDenied("You do not have permission to view this receipt.")
        
        if booking.insurance_payment <= 0:
            raise Http404("No insurance receipt available for this booking.")
        
        return booking

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.object
        
        # Add all required data to context
        context['product_name'] = booking.product_name
        context['product_value'] = booking.product_value
        context['insurance_payment'] = booking.insurance_payment
        context['client_full_name'] = booking.client.get_full_name()
        context['client_email'] = booking.client.email
        context['insurance_company'] = "AXA MANSARD INSURANCE"
        context['current_year'] = timezone.now().year
        context['site_url'] = settings.SITE_URL
        
        return context
        

@method_decorator(login_required, name='dispatch')
class AvailableTruckListView(ListView):
    model = Truck
    template_name = 'booking/booking.html'
    context_object_name = 'available_trucks'
    paginate_by = 10  # Limit to 10 trucks per page

    def get_queryset(self):
        queryset = Truck.objects.filter(available=True).prefetch_related('images')

        # Get filter parameters from the request
        weight_range = self.request.GET.get('weight_range')
        state = self.request.GET.get('state')

        # Apply filters if parameters are provided
        if weight_range:
            queryset = queryset.filter(weight_range=weight_range)
        if state:
            queryset = queryset.filter(state__icontains=state)  # Use icontains for partial matches

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter parameters to the context
        context['weight_range'] = self.request.GET.get('weight_range', '')
        context['state'] = self.request.GET.get('state', '')
        return context










# ADMIN


# booking/views.py - Fix the AdminTruckListView

@method_decorator(admin_required, name='dispatch')
class AdminTruckListView(View):
    template_name = 'booking/admin_truck_list.html'
    success_url = reverse_lazy('admin_truck_list')

    def get(self, request):
        # Show trucks that are not available (both activated and non-activated)
        trucks = Truck.objects.filter(available=False).prefetch_related('images')
        
        # Add filter options
        activation_filter = request.GET.get('activation_status', 'all')
        if activation_filter == 'activated':
            trucks = trucks.filter(activated=True)
        elif activation_filter == 'not_activated':
            trucks = trucks.filter(activated=False)
        elif activation_filter == 'payment_activated':
            trucks = trucks.filter(activated=True, activation_method='payment')
        elif activation_filter == 'manual_activated':
            trucks = trucks.filter(activated=True, activation_method='manual')
        
        paginator = Paginator(trucks, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        form = TruckApprovalForm()
        activation_form = TruckActivationForm()
        deactivation_form = TruckDeactivationForm()
        
        context = {
            'page_obj': page_obj,
            'form': form,
            'activation_form': activation_form,
            'deactivation_form': deactivation_form,
            'activation_filter': activation_filter,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')
        
        if action == 'approve_trucks':
            return self._handle_truck_approval(request)
        elif action == 'activate_trucks':
            return self._handle_truck_activation(request)
        elif action == 'deactivate_trucks':
            return self._handle_truck_deactivation(request)
        else:
            messages.error(request, 'Invalid action.')
            return redirect(self.success_url)

    def _handle_truck_approval(self, request):
        form = TruckApprovalForm(request.POST)
        if form.is_valid():
            truck_ids = form.cleaned_data.get('truck_ids')
            tracker_id = form.cleaned_data.get('tracker_id')
            activate_trucks = form.cleaned_data.get('activate_trucks', False)
            
            if truck_ids and tracker_id:
                updated_count = 0
                with transaction.atomic():
                    for truck_id in truck_ids:
                        try:
                            truck = Truck.objects.get(id=truck_id)
                            truck.available = True
                            truck.tracker_id = tracker_id
                            if activate_trucks and not truck.activated:
                                success, message = truck.activate_truck(
                                    user=request.user, 
                                    tracker_id=tracker_id,
                                    activation_method='manual'
                                )
                                if not success:
                                    logger.warning(f"Failed to activate truck {truck_id}: {message}")
                            truck.save()
                            updated_count += 1
                        except Truck.DoesNotExist:
                            continue
                        except Exception as e:
                            logger.error(f"Error approving truck {truck_id}: {str(e)}")
                            continue
                
                messages.success(
                    request, 
                    f'{updated_count} truck(s) have been approved and {"activated" if activate_trucks else "marked as available"}.'
                )
            else:
                messages.warning(request, 'No trucks were selected for approval or tracker ID is missing.')
        else:
            messages.error(request, 'Invalid form submission.')
        return redirect(self.success_url)

    def _handle_truck_activation(self, request):
        form = TruckActivationForm(request.POST)
        if form.is_valid():
            truck_ids = form.cleaned_data.get('truck_ids')
            tracker_id = form.cleaned_data.get('tracker_id')
            
            if truck_ids:
                activated_count = 0
                failed_activations = []
                
                with transaction.atomic():
                    for truck_id in truck_ids:
                        try:
                            truck = Truck.objects.get(id=truck_id)
                            if not truck.activated:
                                success, message = truck.activate_truck(
                                    user=request.user, 
                                    tracker_id=tracker_id,
                                    activation_method='manual'
                                )
                                if success:
                                    activated_count += 1
                                else:
                                    failed_activations.append(f"{truck.name}: {message}")
                            else:
                                failed_activations.append(f"{truck.name}: Already activated")
                        except Truck.DoesNotExist:
                            failed_activations.append(f"Truck ID {truck_id}: Not found")
                        except Exception as e:
                            logger.error(f"Error activating truck {truck_id}: {str(e)}")
                            failed_activations.append(f"{truck.name}: Activation error")
                
                if activated_count > 0:
                    messages.success(request, f'{activated_count} truck(s) activated successfully.')
                if failed_activations:
                    # Show only first 5 errors to avoid message overflow
                    error_message = 'Some trucks could not be activated: ' + ', '.join(failed_activations[:5])
                    if len(failed_activations) > 5:
                        error_message += f' ... and {len(failed_activations) - 5} more'
                    messages.warning(request, error_message)
            else:
                messages.warning(request, 'No trucks were selected for activation.')
        else:
            # Form validation failed - show specific errors
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            messages.error(request, f'Form errors: {", ".join(error_messages)}')
        return redirect(self.success_url)

    def _handle_truck_deactivation(self, request):
        form = TruckDeactivationForm(request.POST)
        if form.is_valid():
            truck_ids = form.cleaned_data.get('truck_ids')
            reason = form.cleaned_data.get('reason', 'No reason provided')
            
            if truck_ids:
                deactivated_count = 0
                failed_deactivations = []
                
                with transaction.atomic():
                    for truck_id in truck_ids:
                        try:
                            truck = Truck.objects.get(id=truck_id)
                            if truck.activated:
                                success, message = truck.deactivate_truck()
                                if success:
                                    deactivated_count += 1
                                    # Log the deactivation reason
                                    logger.info(f"Truck {truck.id} deactivated by {request.user.username}. Reason: {reason}")
                                else:
                                    failed_deactivations.append(f"{truck.name}: {message}")
                            else:
                                failed_deactivations.append(f"{truck.name}: Not activated")
                        except Truck.DoesNotExist:
                            failed_deactivations.append(f"Truck ID {truck_id}: Not found")
                        except Exception as e:
                            logger.error(f"Error deactivating truck {truck_id}: {str(e)}")
                            failed_deactivations.append(f"{truck.name}: Deactivation error")
                
                if deactivated_count > 0:
                    messages.success(request, f'{deactivated_count} truck(s) deactivated successfully.')
                if failed_deactivations:
                    # Show only first 5 errors to avoid message overflow
                    error_message = 'Some trucks could not be deactivated: ' + ', '.join(failed_deactivations[:5])
                    if len(failed_deactivations) > 5:
                        error_message += f' ... and {len(failed_deactivations) - 5} more'
                    messages.warning(request, error_message)
            else:
                messages.warning(request, 'No trucks were selected for deactivation.')
        else:
            # Form validation failed - show specific errors
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            messages.error(request, f'Form errors: {", ".join(error_messages)}')
        return redirect(self.success_url)


# Add individual truck activation/deactivation views
@method_decorator(admin_required, name='dispatch')
class AdminTruckActivationView(View):
    def post(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        
        if truck.activated:
            messages.info(request, f'Truck "{truck.name}" is already activated.')
            return redirect('admin_truck_detail', pk=pk)
        
        if not truck.can_be_activated():
            messages.error(request, f'Truck "{truck.name}" doesn\'t meet activation criteria.')
            return redirect('admin_truck_detail', pk=pk)
        
        success, message = truck.activate_truck(request.user)
        if success:
            messages.success(request, f'Truck "{truck.name}" activated successfully.')
        else:
            messages.error(request, f'Failed to activate truck: {message}')
        
        return redirect('admin_truck_detail', pk=pk)

@method_decorator(admin_required, name='dispatch')
class AdminTruckDeactivationView(View):
    def post(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        
        if not truck.activated:
            messages.info(request, f'Truck "{truck.name}" is not activated.')
            return redirect('admin_truck_detail', pk=pk)
        
        success, message = truck.deactivate_truck()
        if success:
            messages.success(request, f'Truck "{truck.name}" deactivated successfully.')
        else:
            messages.error(request, f'Failed to deactivate truck: {message}')
        
        return redirect('admin_truck_detail', pk=pk)    
    


@method_decorator(admin_required, name='dispatch')
class AdminTruckDetailView(View):
    template_name = 'booking/admin_truck_detail.html'
    success_url = reverse_lazy('admin_truck_list')

    def get(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        images = truck.images.all()
        context = {
            'truck': truck,
            'images': images,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        truck = get_object_or_404(Truck, pk=pk)
        action = request.POST.get('action')
        tracker_id = request.POST.get('tracker_id')

        if action == 'approve':
            if not tracker_id:
                messages.error(request, 'Tracker ID is required to approve the truck.')
                return redirect('admin_truck_detail', pk=pk)

            # Update truck status
            truck.tracker_id = tracker_id
            truck.available = True
            if not truck.activated:
                success, message = truck.activate_truck(
                    user=request.user, 
                    tracker_id=tracker_id,
                    activation_method='manual'
                )
                if not success:
                    messages.warning(request, f'Truck approved but activation failed: {message}')
            truck.save()
            
            messages.success(
                request, 
                f'Truck "{truck.name}" has been approved and activated.'
            )
        elif action == 'activate':
            if truck.activated:
                messages.info(request, f'Truck "{truck.name}" is already activated.')
            else:
                success, message = truck.activate_truck(
                    user=request.user, 
                    tracker_id=tracker_id,
                    activation_method='manual'
                )
                if success:
                    messages.success(request, f'Truck "{truck.name}" has been activated.')
                else:
                    messages.error(request, f'Failed to activate truck: {message}')
        elif action == 'deactivate':
            if not truck.activated:
                messages.info(request, f'Truck "{truck.name}" is not activated.')
            else:
                success, message = truck.deactivate_truck()
                if success:
                    messages.success(request, f'Truck "{truck.name}" has been deactivated.')
                else:
                    messages.error(request, f'Failed to deactivate truck: {message}')
        elif action == 'reject':
            truck.delete()
            messages.success(request, f'Truck "{truck.name}" has been rejected and removed.')
        else:
            messages.error(request, 'Invalid action.')
        
        return redirect(self.success_url)
    

@method_decorator(admin_required, name='dispatch')
class AdminAllTrucksListView(ListView):
    model = Truck
    template_name = 'booking/admin_all_trucks.html'
    context_object_name = 'trucks'
    paginate_by = 10
    ordering = ['-id']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtering based on query parameters
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(activated=True, available=True)
        elif status == 'pending':
            queryset = queryset.filter(activated=False)
        elif status == 'inactive':
            queryset = queryset.filter(activated=True, available=False)
        return queryset.prefetch_related('images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'all')
        return context


@method_decorator(admin_required, name='dispatch')
class AdminTruckEditView(UpdateView):
    model = Truck
    form_class = TruckEditForm
    template_name = 'booking/admin_truck_edit.html'
    success_url = reverse_lazy('admin_all_trucks')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Truck "{self.object.name}" updated successfully')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below')
        return super().form_invalid(form)


@method_decorator(admin_required, name='dispatch')
class AdminTruckDeleteView(SuccessMessageMixin, DeleteView):
    model = Truck
    template_name = 'booking/admin_truck_confirm_delete.html'
    success_url = reverse_lazy('admin_all_trucks')
    success_message = "Truck deleted successfully"
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


# Booking Update Delivery Cost View
@method_decorator(admin_required, name='dispatch')
class BookingUpdateDeliveryCostView(View):
    template_name = 'booking/booking_list_admin.html'

    def get(self, request):
        """
        Fetch bookings with no delivery cost assigned and display them in a paginated format.
        """
        bookings = Booking.objects.filter(
            delivery_cost=0.00,  # Delivery cost is not set
            payment_completed=True,  # Payment is completed
            booking_status='pending'  # Pending bookings only
        ).select_related('truck', 'client', 'truck__owner')

        # Paginate bookings
        paginator = Paginator(bookings, 5)  # Show 5 bookings per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, self.template_name, {'bookings': page_obj})

    def post(self, request, pk):
        """
        Update the delivery cost for a specific booking.
        """
        booking = get_object_or_404(Booking, pk=pk)
        delivery_cost = request.POST.get("delivery_cost")

        try:
            # Validate delivery cost input
            delivery_cost = Decimal(delivery_cost)
            if delivery_cost <= 0:
                raise ValueError("Invalid delivery cost.")
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid positive delivery cost.")
            return redirect('admin-update-delivery-cost')

        # Update booking with delivery cost and calculate total
        booking.delivery_cost = delivery_cost
        booking.total_delivery_cost = delivery_cost + booking.insurance_payment
        booking.booking_status = 'active'  # Activate booking after assigning cost
        booking.save()

        # Trigger the referral bonus logic
        self._trigger_referral_bonus(booking)

        messages.success(request, f"Delivery cost for Booking {booking.pk} updated successfully.")
        return redirect('admin-update-delivery-cost')

    def _trigger_referral_bonus(self, booking):
        """
        Trigger the referral bonus logic after delivery cost is set.
        """
        user = booking.client  # Use the correct field (e.g., 'client')
        try:
            referral = user.referral_received
            referrer = referral.referrer

            # Explicitly convert delivery_cost to Decimal
            delivery_cost = Decimal(str(booking.delivery_cost))  # Convert to string first, then to Decimal

            # Calculate the bonus_amount using Decimal arithmetic
            bonus_amount = delivery_cost * Decimal('0.015')  # Use Decimal for calculations

            # Add the bonus_amount to the referrer's credits
            referrer.credits += bonus_amount
            referrer.save()

            # Create a ReferralBonus record
            ReferralBonus.objects.create(
                referrer=referrer,
                booking_cost=delivery_cost,  # Use the Decimal value
                bonus_amount=bonus_amount
            )
        except AttributeError:
            # Handle the case where the user has no referral_received
            pass



@method_decorator(admin_required, name='dispatch')
class BookingWithUpdatedCostView(ListView):
    model = Booking
    template_name = 'booking/updated_cost_booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 5  # Show 5 bookings per page

    def get_queryset(self):
        # Fetch bookings where delivery cost is set and prefetch related data
        return Booking.objects.filter(
            delivery_cost__gt=0  # Changed from isnull to greater than 0
        ).select_related(
            'client', 'truck', 'truck__owner'
        ).order_by('-booked_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context if needed
        return context


# @method_decorator(admin_required, name='dispatch')
# class BookingAdminListView(ListView):
#     model = Booking
#     template_name = 'booking/admin_booking_list.html'
#     context_object_name = 'bookings'
#     paginate_by = 10  # Set your desired pagination size

#     def get_queryset(self):
#         # Only show bookings without delivery cost assigned
#         return Booking.objects.filter(delivery_cost=0.00).order_by('-booked_at')

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         # Add any additional context if needed
#         return context

#     def post(self, request, *args, **kwargs):
#         if not request.user.is_superuser:
#             return JsonResponse({"detail": "Permission denied."}, status=403)

#         booking_id = request.POST.get("booking_id")
#         delivery_cost = request.POST.get("delivery_cost")

#         if not booking_id or not delivery_cost:
#             return JsonResponse({"detail": "Booking ID and delivery cost are required."}, status=400)

#         try:
#             booking = Booking.objects.get(pk=booking_id)
#         except Booking.DoesNotExist:
#             return JsonResponse({"detail": "Booking not found."}, status=404)

#         try:
#             delivery_cost = float(delivery_cost)
#         except ValueError:
#             return JsonResponse({"detail": "Invalid delivery cost value."}, status=400)

#         # Update the delivery cost and total delivery cost
#         booking.delivery_cost = delivery_cost
#         booking.total_delivery_cost = booking.delivery_cost + booking.insurance_payment
#         booking.save()

#         messages.success(request, f"Delivery cost updated for booking {booking_id}")
#         return redirect("admin-booking-list")



@method_decorator([login_required, user_type_required('admin')], name='dispatch')
class BookingAdminListView(ListView):
    model = Booking
    template_name = 'booking/admin_booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 10

    def get_queryset(self):
        # Only show bookings without delivery cost assigned
        return Booking.objects.filter(delivery_cost=0.00).order_by('-booked_at')

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return JsonResponse({"detail": "Permission denied."}, status=403)

        booking_id = request.POST.get("booking_id")
        delivery_cost = request.POST.get("delivery_cost")

        if not booking_id or not delivery_cost:
            return JsonResponse({"detail": "Booking ID and delivery cost are required."}, status=400)

        try:
            # Wrap all database operations in a transaction
            with transaction.atomic():
                booking = Booking.objects.select_for_update().get(pk=booking_id)
                
                try:
                    delivery_cost = Decimal(delivery_cost)
                except (ValueError, InvalidOperation):
                    return JsonResponse({"detail": "Invalid delivery cost value."}, status=400)

                # Update the booking costs
                booking.delivery_cost = delivery_cost
                booking.total_delivery_cost = booking.delivery_cost + booking.insurance_payment
                booking.save()

                # Check for referral and apply bonus if exists
                try:
                    referral = Referral.objects.select_related('referrer').get(referred_user=booking.client)
                    referrer = referral.referrer
                    
                    # Calculate referral bonus (1.5% of delivery cost)
                    bonus_amount = delivery_cost * Decimal('0.015')
                    
                    # Create referral bonus record
                    ReferralBonus.objects.create(
                        referrer=referrer,
                        booking_cost=delivery_cost,
                        bonus_amount=bonus_amount
                    )
                    
                    # Update referrer's credits
                    User.objects.filter(pk=referrer.pk).update(
                        credits=models.F('credits') + bonus_amount
                    )
                    
                    messages.success(
                        request, 
                        f"Delivery cost updated for booking {booking_id}. "
                        f"Referral bonus of ₦{bonus_amount:.2f} credited to {referrer.email}"
                    )
                except Referral.DoesNotExist:
                    messages.success(
                        request, 
                        f"Delivery cost updated for booking {booking_id}. No referral bonus applied."
                    )

        except Booking.DoesNotExist:
            return JsonResponse({"detail": "Booking not found."}, status=404)
        except Exception as e:
            # Log the error if needed
            return JsonResponse({"detail": "An error occurred while processing your request."}, status=500)

        return redirect("admin-booking-list")
    


@method_decorator([login_required, user_type_required('admin')], name='dispatch')
class AdminBookingCreateView(CreateView):
    model = Booking
    form_class = AdminBookingForm
    template_name = 'booking/admin_booking_form.html'
    success_url = reverse_lazy('updated_cost_booking_list')

    def form_valid(self, form):
        booking = form.save(commit=False)
        client = booking.client
        
        # Set insurance payment based on client's subscription
        if client:
            active_subscription = UserSubscription.objects.filter(
                user=client,
                subscription_status='active',
                is_active=True
            ).exclude(plan__name=SubscriptionPlan.FREE).first()

            if active_subscription and active_subscription.plan.name == SubscriptionPlan.PREMIUM:
                booking.insurance_payment = float(form.cleaned_data['product_value']) * 0.01
            else:
                booking.insurance_payment = 0
        else:
            booking.insurance_payment = 0

        # Get delivery cost from form and calculate total
        booking.delivery_cost = form.cleaned_data['delivery_cost']
        booking.total_delivery_cost = booking.delivery_cost + booking.insurance_payment
        
        # Mark as admin-created booking
        booking.created_by_admin = True
        booking.save()
        
        return redirect(self.success_url)