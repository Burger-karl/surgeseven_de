from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView, View, DetailView
from django.urls import reverse_lazy
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation
from .forms import TruckForm, BookingForm, TruckApprovalForm, TruckImageForm, AdminBookingForm
from .models import Truck, Booking, TruckImage
from subscriptions.models import UserSubscription, SubscriptionPlan
from users.models import ReferralBonus, Referral, User
from django.db.models import F
from django.db import transaction, models

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


# Truck Create View
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
        image_form = TruckImageForm(self.request.POST, self.request.FILES)

        if form.is_valid() and image_form.is_valid():
            truck = form.save(commit=False)
            truck.owner = self.request.user
            truck.save()

            # Save multiple images properly
            images = self.request.FILES.getlist('image')
            for image in images:
                TruckImage.objects.create(truck=truck, image=image)

            return super().form_valid(form)
        else:
            return self.form_invalid(form)


# Truck List View
@method_decorator(login_required, name='dispatch')
class TruckListView(ListView):
    model = Truck
    template_name = 'booking/truck_list.html'
    context_object_name = 'trucks'

    def get_queryset(self):
        if self.request.user.user_type == 'truck_owner':
            return Truck.objects.filter(owner=self.request.user)
        return Truck.objects.filter(available=True)


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
    

# Generate Receipt View
# @method_decorator(login_required, name='dispatch')
# class GenerateReceiptView(DetailView):
#     model = Booking
#     template_name = 'booking/receipt.html'
#     context_object_name = 'booking'

#     def get_object(self, queryset=None):
#         booking_code = self.kwargs.get('booking_code')
#         booking = get_object_or_404(Booking, booking_code=booking_code)
        
#         # Ensure only the client who made the booking can view the receipt
#         if booking.client != self.request.user:
#             raise PermissionDenied("You do not have permission to view this receipt.")
        
#         return booking

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         booking = self.get_object()
        
#         # Add truck name to the context
#         context['truck_name'] = booking.truck.name
        
#         return context


# views.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@method_decorator(login_required, name='dispatch')
class GenerateReceiptView(DetailView):
    model = Booking
    template_name = 'booking/receipt.html'
    context_object_name = 'booking'

    def get_object(self, queryset=None):
        booking_code = self.kwargs.get('booking_code')
        booking = get_object_or_404(Booking, booking_code=booking_code)
        
        # Ensure only the client who made the booking can view the receipt
        if booking.client != self.request.user:
            raise PermissionDenied("You do not have permission to view this receipt.")
        
        return booking

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.get_object()
        
        # Add truck name to the context
        context['truck_name'] = booking.truck.name
        
        # Check if client has premium subscription
        active_subscription = UserSubscription.objects.filter(
            user=booking.client,
            subscription_status='active',
            is_active=True,
            plan__name=SubscriptionPlan.PREMIUM
        ).first()
        
        context['has_premium'] = active_subscription is not None
        context['insurance_company'] = "Veritas Kapital Assurance"
        
        return context

    def render_to_response(self, context, **response_kwargs):
        booking = context['booking']
        
        # Generate and send email with receipts
        if booking.client.email:
            self.send_receipt_email(booking, context)
        
        return super().render_to_response(context, **response_kwargs)

    def send_receipt_email(self, booking, context):
        # Render both receipts
        booking_receipt_html = render_to_string('booking/receipt_email.html', context)
        plain_message = strip_tags(booking_receipt_html)
        
        # Create email
        subject = f"Your Booking Receipt - #{booking.booking_code}"
        from_email = "noreply@yourdomain.com"
        to_email = booking.client.email
        
        email = EmailMultiAlternatives(
            subject,
            plain_message,
            from_email,
            [to_email]
        )
        email.attach_alternative(booking_receipt_html, "text/html")
        
        # Attach insurance receipt if premium user
        if context['has_premium']:
            insurance_receipt_html = render_to_string('booking/insurance_receipt.html', context)
            email.attach_alternative(insurance_receipt_html, "text/html")
        
        # Send email
        email.send()


@method_decorator(login_required, name='dispatch')
class InsuranceReceiptView(DetailView):
    model = Booking
    template_name = 'booking/insurance_receipt.html'
    context_object_name = 'booking'

    def get_object(self, queryset=None):
        booking_code = self.kwargs.get('booking_code')
        booking = get_object_or_404(Booking, booking_code=booking_code)
        
        # Ensure only the client who made the booking can view the receipt
        if booking.client != self.request.user:
            raise PermissionDenied("You do not have permission to view this receipt.")
        
        # Only show insurance receipt if insurance payment exists
        if booking.insurance_payment <= 0:
            raise Http404("No insurance receipt available for this booking.")
        
        return booking

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = self.get_object()
        context['insurance_company'] = "Veritas Kapital Assurance"
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

# Admin Truck List View with Pagination
@method_decorator(admin_required, name='dispatch')
class AdminTruckListView(View):
    template_name = 'booking/admin_truck_list.html'
    success_url = reverse_lazy('admin_truck_list')

    def get(self, request):
        trucks = Truck.objects.filter(available=False).prefetch_related('images')
        paginator = Paginator(trucks, 5)  # Show 5 trucks per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        form = TruckApprovalForm()
        context = {
            'page_obj': page_obj,
            'form': form,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = TruckApprovalForm(request.POST)
        if form.is_valid():
            truck_ids = form.cleaned_data.get('truck_ids')
            tracker_id = form.cleaned_data.get('tracker_id')  # Get tracker ID from the form
            if truck_ids and tracker_id:
                # Update trucks and assign tracker ID
                updated_count = Truck.objects.filter(id__in=truck_ids).update(available=True, tracker_id=tracker_id)
                messages.success(request, f'{updated_count} truck(s) have been approved and assigned tracker ID: {tracker_id}.')
            else:
                messages.warning(request, 'No trucks were selected for approval or tracker ID is missing.')
        else:
            messages.error(request, 'Invalid form submission.')
        return redirect(self.success_url)    
    
    
# Admin Truck Detail View
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
        tracker_id = request.POST.get('tracker_id')  # Get tracker ID from the form

        if action == 'approve':
            if not tracker_id:
                messages.error(request, 'Tracker ID is required to approve the truck.')
                return redirect('admin_truck_detail', pk=pk)

            # Assign tracker ID and mark as available
            truck.tracker_id = tracker_id
            truck.available = True
            truck.save()
            messages.success(request, f'Truck "{truck.name}" has been approved and assigned tracker ID: {tracker_id}.')
        elif action == 'reject':
            truck.delete()
            messages.success(request, f'Truck "{truck.name}" has been rejected and removed.')
        else:
            messages.error(request, 'Invalid action.')
        return redirect(self.success_url)
    

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