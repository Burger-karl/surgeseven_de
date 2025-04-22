from django.db import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView
from django.views import View
from django.utils import timezone
from django.urls import reverse
from .models import SubscriptionPlan, UserSubscription
from payment.models import Payment
from paystackease import PayStackBase
from payment.paystack_client import PaystackClient
import uuid
from django.contrib.auth.decorators import login_required

# Create your views here.

paystack_client = PaystackClient()


class SubscriptionPlanListView(View):
    def get(self, request):
        subscription_plans = SubscriptionPlan.objects.all()
        context = {
            'subscription_plans': subscription_plans,
        }
        return render(request, 'subscriptions/subscription_plans.html', context)


class UserSubscriptionsView(ListView):
    model = UserSubscription
    template_name = 'subscriptions/user_subscriptions.html'
    context_object_name = 'subscriptions'

    def get_queryset(self):
        return UserSubscription.objects.filter(
            user=self.request.user,
            subscription_status='active'
        ).exclude(plan__name='Free')


class SubscribeView(View):
    def get(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        return render(request, 'subscriptions/subscribe.html', {'plan': plan})

    def post(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        user_subscription = UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            start_date=timezone.now(),
            end_date=timezone.now() + plan.duration
        )
        callback_url = request.build_absolute_uri(reverse('payment-callback', args=[user_subscription.id]))
        response = paystack_client.initialize_transaction(request.user.email, plan.price, callback_url)
        if response['status']:
            authorization_url = response['data']['authorization_url']
            return redirect(authorization_url)
        else:
            return render(request, 'subscriptions/subscribe.html', {'plan': plan, 'error': 'Error initializing payment. Please try again.'})


class PaymentCallbackView(View):
    def get(self, request, subscription_id):
        subscription = get_object_or_404(UserSubscription, id=subscription_id)
        reference = request.GET.get('reference')
        response = paystack_client.verify_transaction(reference)
        if response['status']:
            subscription.subscription_status = 'active'
            subscription.save()
            Payment.objects.create(
                user=request.user,
                subscription=subscription,
                amount=subscription.plan.price,
                reference=reference
            )
            return redirect(reverse('user-subscriptions') + '?message=Subscription successful')
        else:
            subscription.delete()
            return redirect(reverse('subscribe', args=[subscription.plan.id]) + '?error=Payment failed. Please try again.')



@login_required
def create_subscription_payment(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    user = request.user

    # Check if the user already has an active subscription
    if UserSubscription.objects.filter(user=user, subscription_status='active').exists():
        return render(request, 'subscriptions/subscribe.html', {'plan': plan, 'error': 'You already have an active subscription.'})

    # Generate a unique subscription code
    subscription_code = str(uuid.uuid4())

    try:
        # Create a new UserSubscription for the user
        user_subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            start_date=timezone.now(),
            end_date=timezone.now() + plan.duration,
            is_active=False,
            payment_completed=False,
            subscription_status='pending',
            subscription_code=subscription_code
        )

        # Build the callback URL using the generated subscription code
        callback_url = request.build_absolute_uri(reverse('verify-payment', kwargs={'ref': subscription_code}))

        # Initialize Paystack transaction
        response = paystack_client.initialize_transaction(user.email, int(plan.price * 100), subscription_code, callback_url)

        if response['status']:
            return redirect(response['data']['authorization_url'])
        else:
            return render(request, 'subscriptions/subscribe.html', {'plan': plan, 'error': 'Payment initialization failed.'})
    
    except IntegrityError as e:
        return render(request, 'subscriptions/subscribe.html', {'plan': plan, 'error': 'Failed to create subscription. Please try again.'})



class CancelSubscriptionView(LoginRequiredMixin, View):
    def post(self, request):
        # Get the user's current active subscription
        current_subscription = UserSubscription.objects.filter(
            user=request.user, subscription_status='active'
        ).exclude(plan__name='Free').first()

        if not current_subscription:
            return redirect(reverse('user-subscriptions') + '?error=No active subscription found.')

        # Cancel the subscription
        current_subscription.deactivate_subscription()

        # Optionally, assign the user to the free plan
        free_plan = get_object_or_404(SubscriptionPlan, name=SubscriptionPlan.FREE)
        UserSubscription.objects.create(
            user=request.user,
            plan=free_plan,
            start_date=timezone.now(),
            end_date=None,
            is_active=False,
            payment_completed=False,
            subscription_status='inactive'
        )
        
        return redirect(reverse('user-subscriptions') + '?message=Subscription cancelled and returned to free plan')



# class RenewSubscriptionView(LoginRequiredMixin, View):
#     def get(self, request, plan_id):
#         plan = get_object_or_404(SubscriptionPlan, id=plan_id)
#         user_subscription = get_object_or_404(UserSubscription, user=request.user, plan=plan, subscription_status='active')

#         context = {
#             'plan': plan,
#             'user_subscription': user_subscription,
#         }
#         return render(request, 'subscriptions/renew_subscription.html', context)

#     def post(self, request, subscription_id):
#         # Fetch the active subscription
#         subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user, subscription_status='active')
        
#         try:
#             # Initialize payment for the renewal
#             subscription_code = str(uuid.uuid4())
#             callback_url = request.build_absolute_uri(reverse('payment-callback', args=[subscription.id]))
#             response = paystack_client.initialize_transaction(request.user.email, int(subscription.plan.price * 100), callback_url)

#             if response['status']:
#                 # Update the subscription with the new payment reference and status
#                 subscription.subscription_code = subscription_code
#                 subscription.subscription_status = 'pending'
#                 subscription.save()

#                 return redirect(response['data']['authorization_url'])
#             else:
#                 context = {
#                     'subscription': subscription,
#                     'plan': subscription.plan,
#                     'error': 'Error initializing payment. Please try again.'
#                 }
#                 return render(request, 'subscriptions/renew_subscription.html', context)

#         except IntegrityError as e:
#             context = {
#                 'subscription': subscription,
#                 'plan': subscription.plan,
#                 'error': 'Failed to renew subscription. Please try again.'
#             }
#             return render(request, 'subscriptions/renew_subscription.html', context)


# class PaymentCallbackView(View):
#     def get(self, request, subscription_id):
#         subscription = get_object_or_404(UserSubscription, id=subscription_id)
#         reference = request.GET.get('reference')
#         response = paystack_client.verify_transaction(reference)

#         if response['status']:
#             if subscription.subscription_status == 'pending':
#                 # Renew the subscription
#                 subscription.renew_subscription()
#                 subscription.payment_completed = True
#                 subscription.subscription_status = 'active'
#                 subscription.save()

#                 Payment.objects.create(
#                     user=request.user,
#                     subscription=subscription,
#                     amount=subscription.plan.price,
#                     reference=reference
#                 )
#                 return redirect(reverse('user-subscriptions') + '?message=Subscription renewed successfully')
#             else:
#                 return redirect(reverse('user-subscriptions') + '?error=Invalid subscription status for renewal.')
#         else:
#             return redirect(reverse('user-subscriptions') + '?error=Payment verification failed. Please try again.')

