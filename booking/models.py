from django.db import models
from django.utils import timezone
from users.models import User
from django.core.exceptions import ValidationError


class Truck(models.Model):
    LIGHTWEIGHT = 'lightweight'
    MEDIUMWEIGHT = 'mediumweight'
    HEAVYWEIGHT = 'heavyweight'
    VERYHEAVYWEIGHT = 'veryheavyweight'

    WEIGHT_CHOICES = [
        (LIGHTWEIGHT, '0 - 15000kg'),
        (MEDIUMWEIGHT, '15000 - 30000kg'),
        (HEAVYWEIGHT, '30000 - 35000kg'),
        (VERYHEAVYWEIGHT, '40000kg - 50000kg')
    ]

    STATES_CHOICES = [
        ('abia', 'Abia'), ('abuja', 'Abuja'), ('adamawa', 'Adamawa'), ('akwa_ibom', 'Akwa Ibom'), ('anambra', 'Anambra'),
        ('bauchi', 'Bauchi'), ('bayelsa', 'Bayelsa'), ('benue', 'Benue'), ('borno', 'Borno'),
        ('cross_river', 'Cross River'), ('delta', 'Delta'), ('ebonyi', 'Ebonyi'), ('edo', 'Edo'),
        ('ekiti', 'Ekiti'), ('enugu', 'Enugu'), ('gombe', 'Gombe'), ('imo', 'Imo'),
        ('jigawa', 'Jigawa'), ('kaduna', 'Kaduna'), ('kano', 'Kano'), ('katsina', 'Katsina'),
        ('kebbi', 'Kebbi'), ('kogi', 'Kogi'), ('kwara', 'Kwara'), ('lagos', 'Lagos'),
        ('nasarawa', 'Nasarawa'), ('niger', 'Niger'), ('ogun', 'Ogun'), ('ondo', 'Ondo'),
        ('osun', 'Osun'), ('oyo', 'Oyo'), ('plateau', 'Plateau'), ('rivers', 'Rivers'),
        ('sokoto', 'Sokoto'), ('taraba', 'Taraba'), ('yobe', 'Yobe'), ('zamfara', 'Zamfara'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    weight_range = models.CharField(max_length=15, choices=WEIGHT_CHOICES, default=LIGHTWEIGHT)
    available = models.BooleanField(default=False)
    state = models.CharField(max_length=20, choices=STATES_CHOICES)
    local_government = models.CharField(max_length=255)
    tracker_id = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Assigned by admin

    def __str__(self):
        return f"{self.name} ({self.owner.username})"
    
    
    def clean(self):
        if self.pk and self.images.count() != 3:
            raise ValidationError("A truck must have exactly 3 images.")



class TruckImage(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='trucks/', default='service-44.jpg')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.truck.name}"
    
    @property
    def is_valid_image(self):
        """Check if the stored file is a valid image"""
        try:
            from PIL import Image
            Image.open(self.image)
            return True
        except:
            return False
            
    @property
    def filesize(self):
        """Return filesize in MB"""
        if self.image:
            return self.image.size / (1024 * 1024)
        return 0


class Booking(models.Model):
    STATES_CHOICES = [
        ('abia', 'Abia'), ('abuja', 'Abuja'), ('adamawa', 'Adamawa'), ('akwa_ibom', 'Akwa Ibom'), ('anambra', 'Anambra'),
        ('bauchi', 'Bauchi'), ('bayelsa', 'Bayelsa'), ('benue', 'Benue'), ('borno', 'Borno'),
        ('cross_river', 'Cross River'), ('delta', 'Delta'), ('ebonyi', 'Ebonyi'), ('edo', 'Edo'),
        ('ekiti', 'Ekiti'), ('enugu', 'Enugu'), ('gombe', 'Gombe'), ('imo', 'Imo'),
        ('jigawa', 'Jigawa'), ('kaduna', 'Kaduna'), ('kano', 'Kano'), ('katsina', 'Katsina'),
        ('kebbi', 'Kebbi'), ('kogi', 'Kogi'), ('kwara', 'Kwara'), ('lagos', 'Lagos'),
        ('nasarawa', 'Nasarawa'), ('niger', 'Niger'), ('ogun', 'Ogun'), ('ondo', 'Ondo'),
        ('osun', 'Osun'), ('oyo', 'Oyo'), ('plateau', 'Plateau'), ('rivers', 'Rivers'),
        ('sokoto', 'Sokoto'), ('taraba', 'Taraba'), ('yobe', 'Yobe'), ('zamfara', 'Zamfara'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE)
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE, related_name='bookings')
    product_name = models.CharField(max_length=255)
    product_weight = models.CharField(max_length=15, choices=Truck.WEIGHT_CHOICES)
    product_value = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=11)
    payment_completed = models.BooleanField(default=False)
    booked_at = models.DateTimeField(default=timezone.now)
    pickup_state = models.CharField(max_length=20, choices=STATES_CHOICES)
    destination_state = models.CharField(max_length=20, choices=STATES_CHOICES)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    booking_code = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Ensure uniqueness
    booking_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    insurance_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 

    def __str__(self):
        return f"Booking by {self.client.username} for {self.product_name}"


class Receipt(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2)
    insurance_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_delivery_cost = models.DecimalField(max_digits=10, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt for Booking {self.booking.id} - Total Cost: {self.total_delivery_cost}"