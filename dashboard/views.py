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
from django.db.models import Q, Prefetch, Count
from django.db import models 
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth import get_user_model
from tracker.services import get_tracker_data

User = get_user_model()

# Create your views here.

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
    

@method_decorator(login_required, name='dispatch')
class ClientDashboardView(TemplateView):
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
        
        # Unpaid bookings
        unpaid_bookings = Booking.objects.filter(client=user, payment_completed=False).values(
            'id', 'truck__name', 'product_name', 'product_value', 'pickup_state', 'destination_state', 'delivery_cost'
        )

        # Paid bookings
        paid_bookings = Booking.objects.filter(client=user, payment_completed=True).values(
            'id', 'truck__name', 'product_name', 'product_value', 'pickup_state', 
            'destination_state', 'delivery_cost'
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
        referral_credits = user.credits

        # Tracked trucks (trucks with trackers that are booked by the client)
        tracked_trucks = Truck.objects.filter(
            bookings__client=user,
            tracker_id__isnull=False
        ).distinct().select_related('owner').prefetch_related('bookings')

        # Paginate tracked trucks
        page = self.request.GET.get('page', 1)
        paginator = Paginator(tracked_trucks, 5)  # 5 trucks per page
        try:
            tracked_trucks_page = paginator.page(page)
        except PageNotAnInteger:
            tracked_trucks_page = paginator.page(1)
        except EmptyPage:
            tracked_trucks_page = paginator.page(paginator.num_pages)

        # Add tracker data to each truck
        for truck in tracked_trucks_page.object_list:
            truck.tracker_data = get_tracker_data(truck.tracker_id, self.request.user)

        # Context data
        context.update({
            'profile': profile_data,
            'subscription': subscription_data,
            'unpaid_bookings': list(unpaid_bookings),
            'paid_bookings': list(paid_bookings),
            'delivery_schedules': list(delivery_schedules),
            'delivery_histories': list(delivery_histories),
            'payment_history': list(payment_history),
            'referral_credits': referral_credits,
            'tracked_trucks_page': tracked_trucks_page,
        })

        return context
    

@method_decorator(login_required, name='dispatch')
class TruckOwnerDashboardView(TemplateView):
    template_name = 'dashboard/truck_owner_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Profile details
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

        # Truck details - Fixed queries
        pending_trucks = Truck.objects.filter(owner=user, available=False).annotate(
            first_image_url=models.Subquery(
                TruckImage.objects.filter(truck=models.OuterRef('pk')).values('image')[:1]
            ),
            image_count=Count('images')
        ).values('id', 'name', 'weight_range', 'first_image_url', 'state', 'image_count')

        available_trucks = Truck.objects.filter(owner=user, available=True).annotate(
            first_image_url=models.Subquery(
                TruckImage.objects.filter(truck=models.OuterRef('pk')).values('image')[:1]
            ),
            image_count=Count('images')
        ).values('id', 'name', 'weight_range', 'first_image_url', 'state', 'image_count')

        # Active bookings
        active_bookings = Booking.objects.filter(
            truck__owner=user, booking_status='active', payment_completed=True
        ).select_related('client', 'truck').values(
            'id', 'product_name', 'product_value', 'pickup_state', 'destination_state',
            'delivery_cost', 'client__username', 'truck__name', 'truck__weight_range'
        )

        # Delivery histories
        delivery_histories = DeliveryHistory.objects.filter(
            booking__truck__owner=user
        ).select_related('booking', 'booking__truck').values(
            'booking__truck__name', 'booking__product_name', 'booking__destination_state',
            'booking__insurance_payment', 'booking__total_delivery_cost'
        )

        # Payment history
        payment_history = Payment.objects.filter(
            booking__truck__owner=user
        ).select_related('booking').values(
            'amount', 'ref', 'booking__product_name', 'date_created'
        ).order_by('-date_created')

        # Tracked trucks (trucks with trackers that are currently booked)
        tracked_trucks = Truck.objects.filter(
            owner=user,
            tracker_id__isnull=False,
            bookings__booking_status='active'
        ).distinct().prefetch_related(
            Prefetch('bookings', queryset=Booking.objects.select_related('client'))
        )

        # Add tracker data to each truck before pagination
        for truck in tracked_trucks:
            truck.tracker_data = get_tracker_data(truck.tracker_id, self.request.user)  

        # Paginate tracked trucks
        page = self.request.GET.get('page', 1)
        paginator = Paginator(tracked_trucks, 5)  # 5 trucks per page
        try:
            tracked_trucks_page = paginator.page(page)
        except PageNotAnInteger:
            tracked_trucks_page = paginator.page(1)
        except EmptyPage:
            tracked_trucks_page = paginator.page(paginator.num_pages)

        context.update({
            'profile': profile_data,
            'pending_trucks': list(pending_trucks),
            'available_trucks': list(available_trucks),
            'active_bookings': list(active_bookings),
            'delivery_histories': list(delivery_histories),
            'payment_history': list(payment_history),
            'referral_credits': user.credits,
            'tracked_trucks_page': tracked_trucks_page,
        })

        return context
    

@method_decorator(login_required, name='dispatch')
class AdminDashboardView(TemplateView):
    template_name = 'dashboard/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # User statistics
        context['verified_users_count'] = User.objects.filter(is_verified=True).count()
        context['active_users_count'] = User.objects.filter(is_active=True).count()
        
        # Booking statistics
        context['paid_bookings_count'] = Booking.objects.filter(payment_completed=True).count()
        context['unpaid_bookings_count'] = Booking.objects.filter(payment_completed=False).count()
        
        # Delivery statistics
        context['delivery_schedules_count'] = DeliverySchedule.objects.count()
        context['delivery_histories_count'] = DeliveryHistory.objects.count()
        
        # Truck statistics
        context['pending_trucks_count'] = Truck.objects.filter(available=False).count()
        context['available_trucks_count'] = Truck.objects.filter(available=True).count()
        
        # Tracking statistics
        tracked_trucks = Truck.objects.filter(tracker_id__isnull=False)
        context['tracked_trucks_count'] = tracked_trucks.count()

        # Count online trucks
        online_count = 0
        for truck in tracked_trucks:
            tracker_data = get_tracker_data(truck.tracker_id, self.request.user)
            if tracker_data and tracker_data.get('status') == 'online':
                online_count += 1
        context['online_trucks_count'] = online_count
        
        # Paginated lists
        page = self.request.GET.get('page', 1)
        
        # Paid bookings with pagination
        paid_bookings = Booking.objects.filter(payment_completed=True).select_related('client', 'truck')
        paid_paginator = Paginator(paid_bookings, 10)
        context['paid_bookings'] = paid_paginator.get_page(page)
        
        # Unpaid bookings with pagination
        unpaid_bookings = Booking.objects.filter(payment_completed=False).select_related('client', 'truck')
        unpaid_paginator = Paginator(unpaid_bookings, 10)
        context['unpaid_bookings'] = unpaid_paginator.get_page(page)
        
        # Delivery schedules with pagination
        delivery_schedules = DeliverySchedule.objects.select_related('booking', 'booking__client', 'booking__truck')
        schedule_paginator = Paginator(delivery_schedules, 10)
        context['delivery_schedules'] = schedule_paginator.get_page(page)
        
        # Delivery histories with pagination
        delivery_histories = DeliveryHistory.objects.select_related('booking', 'booking__client', 'booking__truck')
        history_paginator = Paginator(delivery_histories, 10)
        context['delivery_histories'] = history_paginator.get_page(page)
        
        # Pending trucks with pagination
        pending_trucks = Truck.objects.filter(available=False).select_related('owner').annotate(
            image_count=Count('images')
        )
        pending_paginator = Paginator(pending_trucks, 10)
        context['pending_trucks'] = pending_paginator.get_page(page)
        
        # Available trucks with pagination
        available_trucks = Truck.objects.filter(available=True).select_related('owner').annotate(
            image_count=Count('images')
        )
        available_paginator = Paginator(available_trucks, 10)
        context['available_trucks'] = available_paginator.get_page(page)
        
        # Tracked trucks with pagination
        tracked_trucks = Truck.objects.filter(
            tracker_id__isnull=False
        ).select_related('owner').prefetch_related(
            Prefetch('bookings', queryset=Booking.objects.filter(booking_status='active'))
        )  # Added missing closing parenthesis here

        # Add tracker data to each truck
        for truck in tracked_trucks:
            truck.tracker_data = get_tracker_data(truck.tracker_id, self.request.user)

        tracked_paginator = Paginator(tracked_trucks, 10)
        context['tracked_trucks'] = tracked_paginator.get_page(page)
        
        # Payment history
        payments = Payment.objects.select_related('user', 'subscription', 'booking').order_by('-date_created')
        payment_paginator = Paginator(payments, 10)
        context['payments'] = payment_paginator.get_page(page)
        
        return context