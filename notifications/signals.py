from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification
from booking.models import Booking, Truck
from payment.models import Payment
from delivery.models import DeliveryHistory
from subscriptions.models import SubscriptionPlan
from users.models import User
from utils import is_migration_running  # Helper function to check if migrations are running

@receiver(post_save, sender=Booking)
def handle_booking_notifications(sender, instance, created, **kwargs):
    if is_migration_running():
        return

    # Cache superuser
    superuser = User.objects.filter(is_superuser=True).first()

    if created:
        # Notify the superuser and client about new booking
        if superuser:
            Notification.objects.create(
                user=superuser,
                booking=instance,
                message=f"A new booking has been made by {instance.client.username} and is awaiting delivery cost assignment.",
                notification_type="booking-created",
            )

        if instance.client:
            Notification.objects.create(
                user=instance.client,
                booking=instance,
                message="Your booking has been created successfully. Waiting for delivery cost assignment.",
                notification_type="booking-created",
            )


    # Notify relevant users when payment is completed
    if instance.payment_completed and instance.booking_status == 'active':
        Notification.objects.create(
            user=instance.truck.owner,
            booking=instance,
            truck=instance.truck,
            message="Your truck has been successfully booked and paid for.",
            notification_type="truck-booked",
        )
        # Notification.objects.create(
        #     user=instance.client,
        #     booking=instance,
        #     message="Your booking payment has been verified.",
        #     notification_type="booking-payment-verified",
        # )


@receiver(post_save, sender=Booking)
def notify_client_on_delivery_cost(sender, instance, created, **kwargs):
    if instance.delivery_cost and not instance.payment_completed:
        # Prevent duplicate notifications
        if not Notification.objects.filter(
            user=instance.client,
            booking=instance,
            notification_type="booking-cost-added"
        ).exists():
            Notification.objects.create(
                user=instance.client,
                booking=instance,
                message="The delivery cost for your booking has been set by the admin.",
                notification_type="booking-cost-added",
            )


@receiver(post_save, sender=Payment)
def handle_payment_notifications(sender, instance, created, **kwargs):
    if is_migration_running():  
        return

    if created and instance.verified:
        if instance.booking:
            Notification.objects.create(
                user=instance.booking.client,
                booking=instance.booking,
                message="Your booking payment has been successfully verified.",
                notification_type="booking-payment-verified",
            )
        elif instance.subscription:
            Notification.objects.create(
                user=instance.user,  
                booking=None,
                message="Your subscription payment has been successfully verified.",
                notification_type="subscription-payment-verified",  
            )


@receiver(post_save, sender=DeliveryHistory)
def handle_delivery_notifications(sender, instance, created, **kwargs):
    if is_migration_running():
        return

    if instance.status == 'delivered' and created:
        if instance.booking.client and instance.booking.truck.owner:
            # Prevent duplicate notifications
            if not Notification.objects.filter(
                user=instance.booking.client,
                booking=instance.booking,
                notification_type="delivery-completed"
            ).exists():
                Notification.objects.create(
                    user=instance.booking.client,
                    booking=instance.booking,
                    truck=instance.booking.truck,  # Ensure truck ID is included
                    message="Your delivery has been successfully completed.",
                    notification_type="delivery-completed",
                )

            if not Notification.objects.filter(
                user=instance.booking.truck.owner,
                booking=instance.booking,
                notification_type="delivery-completed"
            ).exists():
                Notification.objects.create(
                    user=instance.booking.truck.owner,
                    booking=instance.booking,
                    truck=instance.booking.truck,  # Ensure truck ID is included
                    message="Your truck has successfully completed a delivery.",
                    notification_type="delivery-completed",
                )


@receiver(post_save, sender=Truck)
def handle_truck_notifications(sender, instance, created, **kwargs):
    if is_migration_running():
        return

    # Cache superuser
    superuser = User.objects.filter(is_superuser=True).first()

    if created:
        # Notify superuser and owner on truck upload
        if superuser and instance.owner:
            Notification.objects.bulk_create([
                Notification(
                    user=superuser,
                    truck=instance,
                    message=f"A new truck has been uploaded by {instance.owner.username} and is awaiting inspection.",
                    notification_type="truck-uploaded",
                ),
                Notification(
                    user=instance.owner,
                    truck=instance,
                    message="Your truck has been uploaded and is awaiting inspection.",
                    notification_type="truck-uploaded",
                ),
            ])


    if instance.available:
        # Notify truck owner when status is updated to available
        Notification.objects.create(
            user=instance.owner,
            truck=instance,
            message="Your truck status has been updated to available after inspection.",
            notification_type="truck-available",
        )



# notifications/signals.py
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Notification, PushSubscription
from pywebpush import webpush, WebPushException
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Notification)
def send_push_notification(sender, instance, created, **kwargs):
    if not created or instance.push_sent:
        return
    
    # Get all push subscriptions for the user
    subscriptions = PushSubscription.objects.filter(user=instance.user)
    
    # Determine base URL
    base_url = getattr(settings, 'BASE_URL', None)
    if not base_url:
        # Fallback to first allowed host with https
        if settings.ALLOWED_HOSTS:
            host = settings.ALLOWED_HOSTS[0]
            base_url = f"https://{host}"
        else:
            logger.error("BASE_URL not set and no ALLOWED_HOSTS defined")
            return
    
    # Build notification URL
    notification_url = f"{base_url}/notifications/{instance.id}/"
    
    for subscription in subscriptions:
        payload = {
            "title": "Surgeseven Notification",
            "body": instance.message,
            "icon": f"{settings.STATIC_URL}assets/img/surge-seven-2.png",
            "badge": f"{settings.STATIC_URL}assets/img/surge-seven-3.png",
            "url": notification_url
        }
        
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "auth": subscription.auth,
                        "p256dh": subscription.p256dh
                    }
                },
                data=json.dumps(payload),
                vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
                vapid_claims={
                    "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"
                }
            )
            instance.push_sent = True
            instance.save()
        except WebPushException as e:
            logger.error(f"WebPush failed for user {instance.user.id}: {e}")
            # Remove invalid subscriptions
            if "410" in str(e) or "404" in str(e):  # Subscription expired or not found
                subscription.delete()            