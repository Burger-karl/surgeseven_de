from django.db import models
from datetime import timedelta, timezone
from users.models import User


class Feature(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class SubscriptionPlan(models.Model):
    FREE = 'free'
    BASIC = 'basic'
    PREMIUM = 'premium'
    PLAN_CHOICES = [
        (FREE, 'Free'),
        (BASIC, 'Basic'),
        (PREMIUM, 'Premium'),
    ]

    name = models.CharField(max_length=10, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration = models.DurationField(default=timedelta(days=0))  # Free plan has no duration
    plan_code = models.CharField(max_length=100, default='default_plan_code')
    features = models.ManyToManyField(Feature, related_name="subscription_plans")

    def __str__(self):
        return self.name
    
    def get_features_list(self):
        # Retrieve the names of all related Feature objects as a list
        return list(self.features.values_list('name', flat=True))

    @classmethod
    def create_default_plans(cls):
        # Ensure default features exist
        booking_app, _ = Feature.objects.get_or_create(name="Booking app")
        tracking_system, _ = Feature.objects.get_or_create(name="Tracking System")
        insurance_coverage, _ = Feature.objects.get_or_create(name="Insurance Coverage")

        # Create or update the Free plan
        free_plan, _ = cls.objects.get_or_create(
            name=cls.FREE,
            defaults={
                'price': 0.00,
                'duration': timedelta(days=0),  # Unlimited duration
            }
        )
        free_plan.features.set([])  # No features for the free plan

        # Create or update the Basic plan
        basic_plan, _ = cls.objects.get_or_create(
            name=cls.BASIC,
            defaults={
                'price': 3000.00,
                'duration': timedelta(days=180),  # 6 months
            }
        )
        # Update features for the basic plan
        basic_plan.features.set([booking_app, tracking_system])

        # Create or update the Premium plan
        premium_plan, _ = cls.objects.get_or_create(
            name=cls.PREMIUM,
            defaults={
                'price': 5000.00,
                'duration': timedelta(days=180),  # 6 months
            }
        )
        # Update features for the premium plan
        premium_plan.features.set([booking_app, tracking_system, insurance_coverage])



class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    payment_completed = models.BooleanField(default=False)
    subscription_status = models.CharField(max_length=10, default='inactive')
    subscription_code = models.CharField(max_length=100, null=True, blank=True)  # Subscription code for Paystack

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

    def activate_subscription(self):
        if self.plan and self.plan.duration:
            self.is_active = True
            self.subscription_status = 'active'
            self.end_date = timezone.now() + self.plan.duration
            self.save()

    @classmethod
    def can_user_subscribe(cls, user):
        active_subscriptions = cls.objects.filter(user=user, is_active=True)
        return not active_subscriptions.exists()

    def deactivate_subscription(self):
        self.is_active = False
        self.subscription_status = 'inactive'
        self.save()


