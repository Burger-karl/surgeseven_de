from django.views.generic import ListView, TemplateView
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator
from users.models import User
from subscriptions.models import UserSubscription
from booking.models import Booking, Truck, TruckImage
from delivery.models import DeliverySchedule, DeliveryHistory
from payment.models import Payment
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Prefetch
from django.db import models 


# Create your views here.


# @method_decorator(login_required, name='dispatch')
# class ClientHomeView(ListView):
#     model = Truck
#     template_name = 'dashboard/client_home.html'
#     context_object_name = 'available_trucks'

#     def get_queryset(self):
#         return Truck.objects.filter(available=True).prefetch_related(
#             Prefetch('images', queryset=TruckImage.objects.all(), to_attr='truck_images')
#         )

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['message'] = "Welcome Client!"
#         return context

#     def get(self, request, *args, **kwargs):
#         user = request.user
#         referral_link = user.generate_referral_link()  # Generate the referral link
#         referral_code = user.referral_code  # Get the referral code

#         context = {
#             'referral_link': referral_link,
#             'referral_code': referral_code,
#         }
#         return context


# @method_decorator(login_required, name='dispatch')
# class TruckOwnerHomeView(ListView):
#     model = Truck
#     template_name = 'dashboard/truck_owner_home.html'
#     context_object_name = 'available_trucks'

#     def get_queryset(self):
#         return Truck.objects.filter(available=True).prefetch_related(
#             Prefetch('images', queryset=TruckImage.objects.all(), to_attr='truck_images')
#         )

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['message'] = "Welcome Client!"
#         return context

@method_decorator(login_required, name='dispatch')
class ClientHomeView(ListView):
    model = Truck
    template_name = 'dashboard/client_home.html'
    context_object_name = 'available_trucks'

    def get_queryset(self):
        return Truck.objects.filter(available=True).prefetch_related(
            Prefetch('images', queryset=TruckImage.objects.all(), to_attr='truck_images')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['message'] = "Welcome Client!"
        context['referral_link'] = user.generate_referral_link()
        context['referral_code'] = user.referral_code
        return context


@method_decorator(login_required, name='dispatch')
class TruckOwnerHomeView(ListView):
    model = Truck
    template_name = 'dashboard/truck_owner_home.html'
    context_object_name = 'available_trucks'

    def get_queryset(self):
        return Truck.objects.filter(available=True).prefetch_related(
            Prefetch('images', queryset=TruckImage.objects.all(), to_attr='truck_images')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['message'] = "Welcome Truck Owner!"  # Changed from "Welcome Client!"
        context['referral_link'] = user.generate_referral_link()
        context['referral_code'] = user.referral_code
        return context


@method_decorator(login_required, name='dispatch')
class AdminHomeView(TemplateView):
    template_name = 'dashboard/admin_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = "Welcome Admin!"
        return context


@method_decorator(login_required,name='dispatch')
class AboutView(View):
    def get(self, request):
        return render(request, 'dashboard/about.html')
    


class ClientDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/client_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Profile details (handle case where profile does not exist)
        try:
            profile_data = {
                'profile_image': user.profile.profile_image.url if user.profile.profile_image else None,
                'full_name': user.profile.full_name,
                'address': user.profile.address,
                'phone_number': user.profile.phone_number,
                'state': user.profile.state,
            }
        except AttributeError:
            profile_data = {
                'profile_image': None,
                'full_name': 'No Profile',
                'address': 'No Address',
                'phone_number': 'No Phone Number',
                'state': 'No State',
            }
        
        # Current subscription details
        try:
            subscription = UserSubscription.objects.get(user=user, subscription_status='active')
            subscription_data = {
                'plan': subscription.plan.name if subscription.plan else "No Plan",
                'start_date': subscription.start_date,
                'end_date': subscription.end_date,
            }
        except UserSubscription.DoesNotExist:
            subscription_data = None
        
        # Unpaid bookings (payment_completed = False)
        unpaid_bookings = Booking.objects.filter(client=user, payment_completed=False).values(
            'id', 'truck__name', 'product_name', 'product_value', 'pickup_state', 'destination_state', 'delivery_cost'
        )

        # Delivery schedules
        delivery_schedules = DeliverySchedule.objects.filter(client=user).values(
            'booking__truck__name', 'booking__product_name', 'booking__total_delivery_cost', 
            'booking__destination_state', 'status'
        )

        # Delivery histories
        delivery_histories = DeliveryHistory.objects.filter(client=user).values(
            'booking__truck__name', 'booking__product_name', 'booking__destination_state', 
            'booking__insurance_payment', 'booking__total_delivery_cost'
        )

        # Payment history
        payment_history = Payment.objects.filter(user=user).values(
            'amount', 'ref', 'subscription__name', 'booking__product_name', 'date_created'
        ).order_by('-date_created')

        # Referral credits
        referral_credits = user.credits  # Get the user's referral credits

        # Context data
        context.update({
            'profile': profile_data,
            'subscription': subscription_data,
            'unpaid_bookings': list(unpaid_bookings),
            'delivery_schedules': list(delivery_schedules),
            'delivery_histories': list(delivery_histories),
            'payment_history': list(payment_history),
            'referral_credits': referral_credits,  # Add referral credits to context
        })

        return context
    
    

class TruckOwnerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/truck_owner_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Profile details (handle case where profile does not exist)
        try:
            profile_data = {
                'profile_image': user.profile.profile_image.url if user.profile.profile_image else None,
                'full_name': user.profile.full_name,
                'address': user.profile.address,
                'phone_number': user.profile.phone_number,
                'state': user.profile.state,
            }
        except AttributeError:
            profile_data = {
                'profile_image': None,
                'full_name': 'No Profile',
                'address': 'No Address',
                'phone_number': 'No Phone Number',
                'state': 'No State',
            }

        # Truck details
        pending_trucks = Truck.objects.filter(owner=user, available=False).annotate(
            first_image_url=models.Subquery(
                TruckImage.objects.filter(truck=models.OuterRef('pk')).values('image')[:1]
            )
        ).values('id', 'name', 'weight_range', 'first_image_url', 'state')

        available_trucks = Truck.objects.filter(owner=user, available=True).annotate(
            first_image_url=models.Subquery(
                TruckImage.objects.filter(truck=models.OuterRef('pk')).values('image')[:1]
            )
        ).values('id', 'name', 'weight_range', 'first_image_url', 'state')

        # Bookings for trucks owned by the truck owner
        active_bookings = Booking.objects.filter(
            truck__owner=user, booking_status='active', payment_completed=True
        ).values(
            'id', 'product_name', 'product_value', 'pickup_state', 'destination_state',
            'delivery_cost', 'client__username', 'truck__name', 'truck__weight_range'
        )

        # Delivery histories for trucks owned by the truck owner
        delivery_histories = DeliveryHistory.objects.filter(
            booking__truck__owner=user
        ).values(
            'booking__truck__name', 'booking__product_name', 'booking__destination_state',
            'booking__insurance_payment', 'booking__total_delivery_cost'
        )

        # Payment history for trucks owned by the truck owner
        payment_history = Payment.objects.filter(
            booking__truck__owner=user
        ).values(
            'amount', 'ref', 'booking__product_name', 'date_created'
        ).order_by('-date_created')

        # Referral credits
        referral_credits = user.credits  # Get the user's referral credits

        # Add all context data
        context.update({
            'profile': profile_data,
            'pending_trucks': list(pending_trucks),
            'available_trucks': list(available_trucks),
            'active_bookings': list(active_bookings),
            'delivery_histories': list(delivery_histories),
            'payment_history': list(payment_history),
            'referral_credits': referral_credits,  # Add referral credits to context
        })

        return context