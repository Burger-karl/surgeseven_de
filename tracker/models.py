
from django.db import models
from booking.models import Truck
from django.conf import settings

class Tracker(models.Model):
    truck = models.OneToOneField(Truck, on_delete=models.CASCADE, related_name="tracker")
    last_latitude = models.FloatField(null=True, blank=True)
    last_longitude = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tracker for {self.truck.name} - {self.truck.tracker_id}"


class TrackingEvent(models.Model):
    tracker = models.ForeignKey(Tracker, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    speed = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.event_type} at {self.timestamp} for {self.tracker.truck.name}"


class Geofence(models.Model):
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius = models.PositiveIntegerField(help_text="Radius in meters")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GeofenceAlert(models.Model):
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE)
    geofence = models.ForeignKey(Geofence, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=[('entry', 'Entry'), ('exit', 'Exit')])
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.truck.name} - {self.event_type} - {self.timestamp}"


class TrackerToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'token')

    def __str__(self):
        return f"{self.user.username} - {self.token[:10]}..."
