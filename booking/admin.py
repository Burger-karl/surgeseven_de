from django.contrib import admin
from .models import Truck

# Register your models here.

@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ('name', 'tracker_id')
    search_fields = ('name', 'tracker_id')