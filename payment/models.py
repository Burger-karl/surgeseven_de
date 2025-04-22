from django.db import models
from django.conf import settings
from django.utils import timezone
from paystackease import PayStackBase
from subscriptions.models import UserSubscription

# Create your models here.

paystack_sync = PayStackBase

class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subscription = models.ForeignKey('subscriptions.SubscriptionPlan', null=True, blank=True, on_delete=models.SET_NULL)
    booking = models.ForeignKey('booking.Booking', null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.PositiveIntegerField()
    ref = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    verified = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.subscription:
            return f"{self.user.username} - {self.subscription.name}"
        if self.booking:
            return f"{self.user.username} - Booking {self.booking.id}"
        return f"{self.user.username} - Payment {self.id}"

    def save(self, *args, **kwargs):
        if not self.ref:
            self.ref = paystack_sync.utils.generate_reference()
        super().save(*args, **kwargs)

    def verify_payment(self):
        status, result = paystack_sync.transactions.verify(self.ref)
        if status and result['status']:
            self.verified = True
            self.save()

            if self.subscription:
                user_subscription, created = UserSubscription.objects.get_or_create(
                    user=self.user,
                    subscription=self.subscription,
                    defaults={
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + self.subscription.duration,
                        'is_active': True,
                        'payment_completed': True,
                        'subscription_status': 'active'
                    }
                )
                if not created:
                    user_subscription.payment_completed = True
                    user_subscription.subscription_status = 'active'
                    user_subscription.is_active = True
                    user_subscription.start_date = timezone.now()
                    user_subscription.end_date = timezone.now() + self.subscription.duration
                    user_subscription.save()
            return True
        return False
