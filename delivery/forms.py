from django import forms
from .models import DeliverySchedule

class DeliveryScheduleForm(forms.ModelForm):
    booking_id = forms.IntegerField(widget=forms.HiddenInput())

    class Meta:
        model = DeliverySchedule
        fields = ['scheduled_date', 'status']
