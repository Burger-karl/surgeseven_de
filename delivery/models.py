from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from booking.models import Booking

# Create your models here.

User = get_user_model()

class DeliverySchedule(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered')
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delivery_schedules', null=True)
    scheduled_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Delivery Schedule for Booking {self.booking.id} - {self.status}"


class DeliveryHistory(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delivery_histories', null=True,)
    delivery_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=DeliverySchedule.STATUS_CHOICES)

    def __str__(self):
        return f"Delivery History for Booking {self.booking.id} - {self.status}"


@receiver(post_save, sender=DeliverySchedule)
def move_to_history(sender, instance, **kwargs):
    if instance.status == 'delivered':
        # Create a DeliveryHistory entry when status is 'delivered'
        DeliveryHistory.objects.get_or_create(
            booking=instance.booking,
            client=instance.client,
            status='delivered'
        )
        # Optional: Delete the delivery schedule if you don't need it after it's delivered
        instance.delete()
