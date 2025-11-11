from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from .paystack_client import PaystackClient
from .models import Payment
from subscriptions.models import SubscriptionPlan, UserSubscription
from django.contrib.auth.decorators import login_required
import uuid
from django.contrib import messages
from booking.models import Booking, Truck
import logging
import hashlib
import hmac
import json
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction
from django.core.mail import mail_admins

logger = logging.getLogger(__name__)

# Create your views here.

class PaymentProcessor:
    @staticmethod
    def safe_verify_transaction(reference, max_retries=3):
        """
        Safely verify transaction with retry logic and comprehensive logging
        """
        for attempt in range(max_retries):
            try:
                response = paystack_client.verify_transaction(reference)
                
                if response.get('status'):
                    transaction_data = response['data']
                    
                    logger.info(
                        f"Transaction verification successful - "
                        f"Reference: {reference}, "
                        f"Amount: {transaction_data.get('amount')}, "
                        f"Status: {transaction_data.get('status')}"
                    )
                    
                    return {
                        'success': True,
                        'data': transaction_data,
                        'message': 'Verification successful'
                    }
                else:
                    logger.warning(
                        f"Transaction verification failed - "
                        f"Reference: {reference}, "
                        f"Attempt: {attempt + 1}, "
                        f"Error: {response.get('message')}"
                    )
                    
                    if attempt == max_retries - 1:
                        return {
                            'success': False,
                            'error': response.get('message', 'Verification failed'),
                            'should_retry': False
                        }
                    
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Network error during verification - "
                    f"Reference: {reference}, "
                    f"Attempt: {attempt + 1}, "
                    f"Error: {str(e)}"
                )
                
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': 'Network error during verification',
                        'should_retry': True
                    }
    
    @staticmethod
    def monitor_payment_health():
        """
        Monitor payment system health and send alerts for issues
        """
        from django.utils import timezone
        from .models import Payment
        
        failed_payments = Payment.objects.filter(
            verified=False,
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).count()
        
        if failed_payments > 10:  # Threshold for alerts
            mail_admins(
                'High Payment Failure Rate',
                f'Detected {failed_payments} failed payments in the last hour.'
            )

# paystack_client = PaystackClient()

# @login_required
# def create_subscription_payment(request, plan_id):
#     plan = get_object_or_404(SubscriptionPlan, id=plan_id)
#     user = request.user
#     amount = int(plan.price * 100)  # Paystack expects amount in kobo (1 Naira = 100 kobo)
#     email = user.email
#     subscription_code = str(uuid.uuid4())  # Generate a unique subscription code

#     # Create a UserSubscription with an initial status
#     user_subscription = UserSubscription.objects.create(
#         user=user,
#         plan=plan,
#         start_date=timezone.now(),
#         end_date=timezone.now() + plan.duration,
#         is_active=False,
#         payment_completed=False,
#         subscription_status='pending',
#         subscription_code=subscription_code
#     )

#     # Build the callback URL using the generated subscription code
#     callback_url = request.build_absolute_uri(reverse('verify-payment', kwargs={'ref': subscription_code}))

#     # Initialize Paystack transaction
#     response = paystack_client.initialize_transaction(email, amount, subscription_code, callback_url)

#     if response['status']:
#         return redirect(response['data']['authorization_url'])
#     else:
#         return render(request, 'subscriptions/subscribe.html', {'plan': plan, 'error': 'Payment initialization failed.'})



# @login_required
# def verify_payment(request, ref):
#     # Verify the payment with Paystack using the reference
#     response = paystack_client.verify_transaction(ref)

#     if response['status'] and response['data']['status'] == 'success':
#         # Update the subscription status or perform other actions
#         user_subscription = UserSubscription.objects.get(subscription_code=ref)
#         user_subscription.payment_completed = True
#         user_subscription.is_active = True
#         user_subscription.subscription_status = 'active'
#         user_subscription.save()
#         return redirect('user-subscriptions')
#     else:
#         return render(request, 'subscriptions/subscribe.html', {'error': 'Payment verification failed.'})


# views.py
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from .paystack_client import PaystackClient
from .models import Payment
from subscriptions.models import SubscriptionPlan, UserSubscription
from django.contrib.auth.decorators import login_required
import uuid
from django.contrib import messages
from booking.models import Booking, Truck

logger = logging.getLogger(__name__)

# Initialize Paystack client
paystack_client = PaystackClient()


@login_required
def create_subscription_payment(request, plan_id):
    try:
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)
        user = request.user
        
        # Validate amount
        if plan.price <= 0:
            messages.error(request, 'Invalid subscription amount.')
            return redirect('subscription-plans')
            
        amount = int(plan.price * 100)  # Paystack expects amount in kobo
        email = user.email
        subscription_code = str(uuid.uuid4())

        # Create a UserSubscription with an initial status
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

        # ALSO create a Payment record for webhook processing
        from .models import Payment
        Payment.objects.create(
            user=user,
            amount=amount,
            ref=subscription_code,
            email=email,
            verified=False,
            payment_type=Payment.SUBSCRIPTION
        )

        # Build the callback URL
        callback_url = request.build_absolute_uri(
            reverse('verify-payment', kwargs={'ref': subscription_code})
        )

        # Initialize Paystack transaction
        response = paystack_client.initialize_transaction(email, amount, subscription_code, callback_url)

        if response.get('status'):
            return redirect(response['data']['authorization_url'])
        else:
            user_subscription.delete()  # Clean up failed subscription
            # Also delete the payment record
            Payment.objects.filter(ref=subscription_code).delete()
            
            error_msg = response.get('message', 'Payment initialization failed.')
            messages.error(request, error_msg)
            return redirect('subscription-plans')
            
    except Exception as e:
        logger.error(f"Subscription payment error: {str(e)}")
        messages.error(request, 'An error occurred while processing your payment.')
        return redirect('subscription-plans')
    

@login_required
def verify_payment(request, ref):
    try:
        # Verify the payment with Paystack
        response = paystack_client.verify_transaction(ref)

        if response.get('status') and response['data'].get('status') == 'success':
            user_subscription = UserSubscription.objects.get(subscription_code=ref)
            user_subscription.payment_completed = True
            user_subscription.is_active = True
            user_subscription.subscription_status = 'active'
            user_subscription.save()
            
            messages.success(request, 'Subscription activated successfully!')
            return redirect('user-subscriptions')
        else:
            error_msg = response.get('message', 'Payment verification failed.')
            messages.error(request, error_msg)
            return redirect('subscription-plans')
            
    except UserSubscription.DoesNotExist:
        messages.error(request, 'Subscription not found.')
        return redirect('subscription-plans')
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        messages.error(request, 'An error occurred while verifying your payment.')
        return redirect('subscription-plans')


from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View, TemplateView
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
import uuid
import logging

logger = logging.getLogger(__name__)

from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseRedirect


class CreateBookingPaymentView(LoginRequiredMixin, View):
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        user = request.user

        if booking.payment_completed:
            messages.error(request, 'Payment has already been completed for this booking.')
            return redirect('booking_list')  # Or the appropriate URL

        amount = int(booking.total_delivery_cost * 100)  # Paystack expects amount in kobo
        email = user.email
        booking_code = str(uuid.uuid4())

        booking.payment_completed = False
        booking.booking_code = booking_code
        booking.save()

        callback_url = request.build_absolute_uri(reverse('verify-booking-payment', kwargs={'ref': booking_code}))

        response = paystack_client.initialize_transaction(email, amount, booking_code, callback_url)

        if response['status']:
            # Redirect to the Paystack authorization URL
            return HttpResponseRedirect(response['data']['authorization_url'])
        else:
            booking.booking_code = None
            booking.save()
            messages.error(request, 'Payment initialization failed.')
            return redirect('booking_list')  # Return a response here to avoid returning None






from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View
from django.contrib import messages
from django.http import HttpResponseRedirect
from booking.models import Receipt
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import resend
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Configure Resend
resend.api_key = settings.RESEND_API_KEY

class VerifyBookingPaymentView(LoginRequiredMixin, View):
    def get(self, request, ref, *args, **kwargs):
        response = paystack_client.verify_transaction(ref)
        logger.debug('Paystack verification response: %s', response)

        if response['status'] and response['data']['status'] == 'success':
            booking = get_object_or_404(Booking, booking_code=ref)
            booking.payment_completed = True
            booking.booking_status = 'active'
            booking.save()

            # Create payment record
            Payment.objects.create(
                user=request.user,
                booking=booking,
                amount=booking.delivery_cost,
                ref=ref,
                email=request.user.email,
                verified=True
            )

            # Create the receipt
            receipt = Receipt.objects.create(
                booking=booking,
                delivery_cost=booking.delivery_cost,
                insurance_payment=booking.insurance_payment,
                total_delivery_cost=booking.total_delivery_cost,
            )

            # Prepare email context
            context = {
                'booking': booking,
                'truck_name': booking.truck.name,
                'has_premium': booking.insurance_payment > 0,
                'insurance_company': "AXA MANSARD INSURANCE",
                'receipt': receipt,
                'current_year': timezone.now().year,
                'site_url': settings.SITE_URL
            }

            # Send receipts via Resend
            self.send_receipts_email(booking, context)

            messages.success(request, "Payment successful! Your receipts have been emailed to you.")
            return HttpResponseRedirect(reverse('generate_receipt', kwargs={'booking_code': booking.booking_code}))
        else:
            messages.error(request, "Payment verification failed.")
            return HttpResponseRedirect(reverse('booking_list'))

    def send_receipts_email(self, booking, context):
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
            
            # If premium user, include insurance receipt
            if context['has_premium']:
                insurance_receipt_html = render_to_string('booking/emails/insurance_receipt.html', context)
                # Note: Resend doesn't support multiple HTML parts in one email
                # We'll combine both receipts in one email or send separately
                # For now, we'll include insurance details in the main receipt
            
            # Send email using Resend
            response = resend.Emails.send(params)
            logger.info(f"Payment receipt email sent to {booking.client.email}. Resend ID: {response['id']}")
            
        except Exception as e:
            logger.error(f"Error sending payment receipt email: {str(e)}")



# payment/views.py - Update the truck activation payment views

import logging
from django.db import transaction

logger = logging.getLogger(__name__)

class CreateTruckActivationPaymentView(LoginRequiredMixin, View):
    def get(self, request, truck_id):
        truck = get_object_or_404(Truck, id=truck_id, owner=request.user)
        
        # Check if already activated
        if truck.activated:
            messages.info(request, 'This truck is already activated.')
            return redirect('truck_list')
        
        # Check for existing pending payment
        existing_payment = Payment.objects.filter(
            truck=truck, 
            payment_type=Payment.TRUCK_ACTIVATION,
            verified=False
        ).first()
        
        if existing_payment:
            # Redirect to existing payment verification
            return redirect('verify-truck-activation-payment', ref=existing_payment.ref)
        
        # Check if truck meets basic criteria for payment activation
        if not truck.images.exists():
            messages.error(request, 'Truck must have images before activation payment.')
            return redirect('truck_list')
        
        context = {
            'truck': truck,
            'amount': 85000,
            'description': 'Truck Activation Fee - Required for inspection and tracker assignment'
        }
        return render(request, 'payment/truck_activation_confirmation.html', context)
    
    def post(self, request, truck_id):
        truck = get_object_or_404(Truck, id=truck_id, owner=request.user)
        
        # Prevent duplicate activation
        if truck.activated:
            messages.info(request, 'This truck is already activated.')
            return redirect('truck_list')
        
        amount = 85000 * 100  # Convert to kobo
        email = request.user.email
        reference = str(uuid.uuid4())
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            truck=truck,
            amount=amount,
            ref=reference,
            email=email,
            verified=False,
            payment_type=Payment.TRUCK_ACTIVATION
        )
        
        callback_url = request.build_absolute_uri(
            reverse('verify-truck-activation-payment', kwargs={'ref': reference})
        )
        
        response = paystack_client.initialize_transaction(email, amount, reference, callback_url)
        
        if response['status']:
            return redirect(response['data']['authorization_url'])
        else:
            payment.delete()
            messages.error(request, 'Payment initialization failed. Please try again.')
            return redirect('truck_list')


class VerifyTruckActivationPaymentView(LoginRequiredMixin, View):
    def get(self, request, ref):
        payment = get_object_or_404(
            Payment, 
            ref=ref, 
            payment_type=Payment.TRUCK_ACTIVATION,
            user=request.user  # Ensure user owns the payment
        )
        
        # Prevent processing already verified payments
        if payment.verified:
            messages.info(request, 'This payment has already been processed.')
            return redirect('truck_list')
        
        response = paystack_client.verify_transaction(ref)
        
        if response['status'] and response['data']['status'] == 'success':
            try:
                with transaction.atomic():
                    payment.verified = True
                    payment.save()
                    
                    # Activate the truck using the payment method
                    truck = payment.truck
                    success, message = truck.activate_via_payment(payment, request.user)
                    
                    if success:
                        # Send notification email using Resend
                        self.send_activation_email(truck)
                        
                        messages.success(
                            request, 
                            'Truck activation payment successful! Your truck will be inspected shortly.'
                        )
                        logger.info(f"Truck {truck.id} activated via payment by user {request.user.username}")
                    else:
                        messages.error(request, f'Truck activation failed: {message}')
                        logger.error(f"Truck activation failed after payment: {message}")
                        
            except Exception as e:
                logger.error(f"Error processing truck activation payment: {str(e)}")
                messages.error(request, 'Error processing payment. Please contact support.')
                
            return redirect('truck_list')
        else:
            messages.error(request, 'Payment verification failed. Please contact support.')
            return redirect('truck_list')
    
    def send_activation_email(self, truck):
        try:
            context = {
                'truck': truck,
                'owner': truck.owner,
                'amount': 85000,
                'current_year': timezone.now().year,
                'site_url': settings.SITE_URL,
                'activation_method': truck.get_activation_status_display()
            }
            
            html_content = render_to_string('payment/emails/truck_activation_receipt.html', context)
            text_content = strip_tags(html_content)
            
            params = {
                "from": f"SurgeSeven <{settings.DEFAULT_FROM_EMAIL}>",
                "to": [truck.owner.email],
                "subject": f"Truck Activation Successful - {truck.name}",
                "html": html_content,
                "text": text_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"Truck activation email sent to {truck.owner.email}. Resend ID: {response['id']}")
            
        except Exception as e:
            logger.error(f"Error sending truck activation email: {str(e)}")



# WITHDRAWAL

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from .models import WithdrawalMethod, WithdrawalRequest
from .forms import WithdrawalMethodForm, WithdrawalRequestForm
import uuid
from django.contrib.admin.views.decorators import staff_member_required



from django.db import transaction
from .services import initiate_flutterwave_payout

@method_decorator(login_required, name='dispatch')
class WithdrawalView(View):
    def post(self, request):
        form = WithdrawalRequestForm(request.user, request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            method = form.cleaned_data['method']
            
            if request.user.credits < amount:
                messages.error(request, "Insufficient balance")
                return redirect('withdraw')

            try:
                with transaction.atomic():
                    # Deduct credits
                    request.user.credits -= amount
                    request.user.save()

                    # Initiate Flutterwave payout
                    payout_data = initiate_flutterwave_payout(
                        account_bank=method.details['bank_code'],
                        account_number=method.details['account_number'],
                        amount=amount,
                        narration=f"SurgeSeven withdrawal",
                        recipient_name=method.details['account_name']
                    )

                    # Create withdrawal record
                    withdrawal = WithdrawalRequest.objects.create(
                        user=request.user,
                        method=method,
                        amount=amount,
                        status='processing',
                        reference=payout_data['data']['reference'],
                        flutterwave_transfer_id=payout_data['data']['id'],
                        flutterwave_reference=payout_data['data']['reference']
                    )

                    messages.success(request, "Withdrawal initiated successfully!")
                    return redirect('withdrawal_history')

            except Exception as e:
                messages.error(request, f"Withdrawal failed: {str(e)}")
                return redirect('withdraw')

        return render(request, self.template_name, {'form': form})
    

@login_required
def add_withdrawal_method(request):
    if request.method == 'POST':
        form = WithdrawalMethodForm(request.POST)
        if form.is_valid():
            method = form.save(commit=False)
            method.user = request.user
            method.save()
            messages.success(request, "Withdrawal method added successfully")
            return redirect('withdraw')
    else:
        form = WithdrawalMethodForm()
    
    return render(request, 'payment/add_withdrawal_method.html', {'form': form})

@login_required
def withdrawal_history(request):
    withdrawals = WithdrawalRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'payment/withdrawal_history.html', {'withdrawals': withdrawals})



# ADMIN

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def process_withdrawals(request):
    pending_withdrawals = WithdrawalRequest.objects.filter(status='pending').order_by('created_at')
    return render(request, 'payment/process_withdrawals.html', {'withdrawals': pending_withdrawals})

@staff_member_required
def update_withdrawal_status(request, withdrawal_id):
    withdrawal = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if status in [choice[0] for choice in WithdrawalRequest.STATUS_CHOICES]:
            withdrawal.status = status
            withdrawal.admin_notes = notes
            if status == 'completed':
                withdrawal.processed_at = timezone.now()
            withdrawal.save()
            messages.success(request, "Withdrawal status updated")
        else:
            messages.error(request, "Invalid status")
        
        return redirect('process_withdrawals')
    
    return render(request, 'payment/update_withdrawal.html', {'withdrawal': withdrawal})



# views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def flutterwave_webhook(request):
    if request.method == 'POST':
        payload = json.loads(request.body)
        transfer_id = payload['data']['id']
        
        try:
            withdrawal = WithdrawalRequest.objects.get(flutterwave_transfer_id=transfer_id)
            withdrawal.status = 'completed' if payload['data']['status'] == 'SUCCESSFUL' else 'failed'
            withdrawal.save()
            return JsonResponse({'status': 'success'})
        except WithdrawalRequest.DoesNotExist:
            return JsonResponse({'status': 'error'}, status=400)