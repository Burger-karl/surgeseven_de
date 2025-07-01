from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager
from django.utils import timezone
from datetime import timedelta
import uuid

# Create your models here.

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('client', 'Client'),
        ('truck_owner', 'Truck Owner'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(max_length=11, choices=USER_TYPE_CHOICES, default='client')
    is_verified = models.BooleanField(default=False)
    email = models.EmailField(unique=True, error_messages={'unique': 'A user with this email already exists.'})
    referral_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)  # Unique referral code for each user
    credits = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Credits for referral bonuses

    # Use email as the unique identifier instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # username is still required but not the primary identifier

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def generate_referral_link(self):
        """Generate a referral link for the user."""
        return f"https://surgeseven.com/register?ref={self.referral_code}"


class Referral(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referred_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referral_received')
    referral_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.referrer.email} referred {self.referred_user.email}"
    


class ReferralBonus(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referral_bonuses')
    booking_cost = models.DecimalField(max_digits=10, decimal_places=2)  # Cost of the booking
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2)  # 1.5% of the booking cost
    bonus_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bonus for {self.referrer.email}: {self.bonus_amount}"

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.created_at + timedelta(minutes=10) < timezone.now()


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.created_at < timezone.now() - timedelta(hours=1)  # 1 hour expiry


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    state = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username