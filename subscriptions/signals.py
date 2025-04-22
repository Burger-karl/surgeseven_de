from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserSubscription, SubscriptionPlan

User = get_user_model()

@receiver(post_save, sender=User)
def create_default_subscription(sender, instance, created, **kwargs):
    if created:
        print(f"Creating default subscription for user {instance}")
        try:
            free_plan = SubscriptionPlan.objects.get(name=SubscriptionPlan.FREE)
            UserSubscription.objects.get_or_create(
                user=instance,
                defaults={'plan': free_plan, 'is_active': False, 'subscription_status': 'inactive'}
            )
            print(f"Assigned Free plan to user {instance}")
        except SubscriptionPlan.DoesNotExist:
            print("Subscription plan 'Free' does not exist.")
