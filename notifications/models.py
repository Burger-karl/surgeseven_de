from django.db import models
from users.models import User
from booking.models import Booking, Truck

# Create your models here.

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('booking-payment-verified', 'Booking Payment Verified'),
        ('subscription-payment-verified', 'Subscription Payment Verified'),
        ('booking-created', 'Booking Created'),
        ('booking-cost-added', 'Booking Cost Added'),
        ('truck-uploaded', 'Truck Uploaded'),
        ('truck-available', 'Truck Available'),
        ('truck-booked', 'Truck Booked'),
        ('delivery-completed', 'Delivery Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='booking-created')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username} - {self.notification_type}"
