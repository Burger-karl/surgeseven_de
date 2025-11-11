# payment/paystack_webhooks.py - UPDATED WITH SUBSCRIPTION SUPPORT

import hashlib
import hmac
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def paystack_webhook(request):
    """
    Production-ready webhook handler for Paystack events
    """
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    # Get signature and payload
    signature = request.headers.get('x-paystack-signature')
    body = request.body
    secret = settings.PAYSTACK_SECRET_KEY
    
    if not signature:
        logger.error("Missing webhook signature")
        return HttpResponse(status=400)
    
    # Verify webhook signature 
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha512
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        logger.error("Invalid webhook signature")
        return HttpResponse(status=400)
    
    try:
        event = json.loads(body.decode('utf-8'))
        event_type = event.get('event')
        data = event.get('data', {})
        
        logger.info(f"Processing webhook event: {event_type}")
        
        # Handle different event types 
        if event_type == 'charge.success':
            return handle_successful_charge(data)
        elif event_type == 'transfer.success':
            return handle_transfer_success(data)
        elif event_type == 'transfer.failed':
            return handle_transfer_failed(data)
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return HttpResponse(status=200)
            
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return HttpResponse(status=500)

def handle_successful_charge(data):
    """
    Handle successful charge events - PRIMARY payment verification method
    """
    try:
        with transaction.atomic():
            reference = data.get('reference')
            amount = data.get('amount')
            
            logger.info(f"Processing successful charge for reference: {reference}")
            
            # Try to find payment in Payment model first
            from .models import Payment
            payment = Payment.objects.filter(ref=reference, verified=False).first()
            
            if payment:
                payment.verified = True
                payment.save()
                logger.info(f"Updated Payment record for reference: {reference}")
                
                # Handle different payment types
                if payment.payment_type == Payment.BOOKING:
                    handle_booking_payment(payment, reference)
                elif payment.payment_type == Payment.TRUCK_ACTIVATION:
                    handle_truck_activation_payment(payment, reference)
                elif payment.payment_type == Payment.SUBSCRIPTION:
                    handle_subscription_payment(payment, reference)
                    
            else:
                # If no Payment record found, check for subscription
                handle_subscription_by_reference(reference)
                
            return HttpResponse(status=200)
            
    except Exception as e:
        logger.error(f"Error handling successful charge: {str(e)}")
        return HttpResponse(status=500)

def handle_booking_payment(payment, reference):
    """Handle booking payment verification"""
    from booking.models import Booking, Receipt
    try:
        booking = Booking.objects.filter(booking_code=reference).first()
        if booking:
            booking.payment_completed = True
            booking.booking_status = 'active'
            booking.save()
            
            # Create receipt if it doesn't exist
            Receipt.objects.get_or_create(
                booking=booking,
                defaults={
                    'delivery_cost': booking.delivery_cost,
                    'insurance_payment': booking.insurance_payment,
                    'total_delivery_cost': booking.total_delivery_cost,
                }
            )
            
            logger.info(f"Booking {booking.id} activated via webhook")
    except Exception as e:
        logger.error(f"Error handling booking payment: {str(e)}")

def handle_truck_activation_payment(payment, reference):
    """Handle truck activation payment verification"""
    from booking.models import Truck
    try:
        truck = payment.truck
        if truck and not truck.activated:
            success, message = truck.activate_via_payment(payment, truck.owner)
            if success:
                logger.info(f"Truck {truck.id} activated via webhook")
            else:
                logger.error(f"Failed to activate truck {truck.id}: {message}")
    except Exception as e:
        logger.error(f"Error handling truck activation payment: {str(e)}")

def handle_subscription_payment(payment, reference):
    """Handle subscription payment from Payment model"""
    from subscriptions.models import UserSubscription
    try:
        # If payment has a subscription reference, update it
        user_subscription = UserSubscription.objects.filter(
            subscription_code=reference
        ).first()
        
        if user_subscription:
            user_subscription.payment_completed = True
            user_subscription.is_active = True
            user_subscription.subscription_status = 'active'
            user_subscription.save()
            logger.info(f"Subscription {user_subscription.id} activated via webhook")
    except Exception as e:
        logger.error(f"Error handling subscription payment: {str(e)}")

def handle_subscription_by_reference(reference):
    """Handle subscription payment when no Payment record exists"""
    from subscriptions.models import UserSubscription
    try:
        user_subscription = UserSubscription.objects.filter(
            subscription_code=reference,
            payment_completed=False
        ).first()
        
        if user_subscription:
            user_subscription.payment_completed = True
            user_subscription.is_active = True
            user_subscription.subscription_status = 'active'
            user_subscription.save()
            
            # Create payment record for audit
            from .models import Payment
            Payment.objects.create(
                user=user_subscription.user,
                amount=user_subscription.plan.price * 100,  # Convert to kobo
                ref=reference,
                email=user_subscription.user.email,
                verified=True,
                payment_type=Payment.SUBSCRIPTION
            )
            
            logger.info(f"Subscription {user_subscription.id} activated via webhook reference")
    except Exception as e:
        logger.error(f"Error handling subscription by reference: {str(e)}")

def handle_transfer_success(data):
    """Handle successful transfer events"""
    logger.info(f"Transfer successful: {data.get('reference')}")
    return HttpResponse(status=200)

def handle_transfer_failed(data):
    """Handle failed transfer events"""
    logger.error(f"Transfer failed: {data.get('reference')}")
    return HttpResponse(status=200)