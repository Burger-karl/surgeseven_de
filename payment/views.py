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
from booking.models import Booking

# Create your views here.

paystack_client = PaystackClient()

@login_required
def create_subscription_payment(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    user = request.user
    amount = int(plan.price * 100)  # Paystack expects amount in kobo (1 Naira = 100 kobo)
    email = user.email
    subscription_code = str(uuid.uuid4())  # Generate a unique subscription code

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

    # Build the callback URL using the generated subscription code
    callback_url = request.build_absolute_uri(reverse('verify-payment', kwargs={'ref': subscription_code}))

    # Initialize Paystack transaction
    response = paystack_client.initialize_transaction(email, amount, subscription_code, callback_url)

    if response['status']:
        return redirect(response['data']['authorization_url'])
    else:
        return render(request, 'subscriptions/subscribe.html', {'plan': plan, 'error': 'Payment initialization failed.'})



@login_required
def verify_payment(request, ref):
    # Verify the payment with Paystack using the reference
    response = paystack_client.verify_transaction(ref)

    if response['status'] and response['data']['status'] == 'success':
        # Update the subscription status or perform other actions
        user_subscription = UserSubscription.objects.get(subscription_code=ref)
        user_subscription.payment_completed = True
        user_subscription.is_active = True
        user_subscription.subscription_status = 'active'
        user_subscription.save()
        return redirect('user-subscriptions')
    else:
        return render(request, 'subscriptions/subscribe.html', {'error': 'Payment verification failed.'})



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


from django.core.mail import send_mail
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View
from django.contrib import messages
from django.http import HttpResponseRedirect
from booking.models import Receipt

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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
                'insurance_company': "Veritas Kapital Assurance",
                'receipt': receipt
            }

            # Send receipts via email
            self.send_receipts_email(booking, context)

            messages.success(request, "Payment successful! Your receipts have been emailed to you.")
            return HttpResponseRedirect(reverse('generate_receipt', kwargs={'booking_code': booking.booking_code}))
        else:
            messages.error(request, "Payment verification failed.")
            return HttpResponseRedirect(reverse('booking_list'))

    def send_receipts_email(self, booking, context):
        # Render both receipts
        booking_receipt_html = render_to_string('booking/receipt_email.html', context)
        plain_message = strip_tags(booking_receipt_html)
        
        # Create email message
        subject = f"Your Booking Receipt - #{booking.booking_code}"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = booking.client.email
        
        # Create SendGrid email
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=booking_receipt_html,
            plain_text_content=plain_message
        )
        
        try:
            # Initialize SendGrid client
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            
            # Attach insurance receipt if applicable
            if context['has_premium']:
                insurance_receipt_html = render_to_string('booking/insurance_receipt_email.html', context)
                message.add_content(insurance_receipt_html, "text/html")
            
            # Send email
            response = sg.send(message)
            logger.info(f"Receipt email sent to {to_email}. Status: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error sending receipt email: {str(e)}")



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