from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Referral, ReferralBonus, Profile
from booking.models import Booking
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def handle_referral_bonus(sender, instance, created, **kwargs):
    """
    Signal to handle referral bonus when a new user is created.
    """
    if created:
        try:
            referral = instance.referral_received
            referrer = referral.referrer
            referrer.credits += 1000
            referrer.save()
        except Referral.DoesNotExist:
            # No referral exists for this user
            pass


@receiver(post_save, sender=Booking)
def handle_booking_referral_bonus(sender, instance, **kwargs):
    """
    Trigger referral bonus logic when a booking's delivery cost is set.
    """
    if instance.delivery_cost > 0:  # Only trigger if delivery cost is set
        user = instance.client  # Use the correct field (e.g., 'client')
        try:
            referral = user.referral_received
            referrer = referral.referrer

            # Explicitly convert delivery_cost to Decimal
            delivery_cost = Decimal(str(instance.delivery_cost))  # Convert to string first, then to Decimal

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


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to create a Profile object for every new User.
    """
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal to save the Profile object whenever the User object is saved.
    """
    instance.profile.save()
    