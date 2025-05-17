from django import forms
from .models import Truck, Booking, TruckImage

class TruckForm(forms.ModelForm):
    class Meta:
        model = Truck
        fields = ['name', 'weight_range', 'state', 'local_government', 'available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter truck name'}),
            'weight_range': forms.Select(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
            'local_government': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter local government'}),
        }


class TruckImageForm(forms.ModelForm):
    class Meta:
        model = TruckImage
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'product_name', 'product_weight', 'product_value', 
            'phone_number', 'pickup_state', 'destination_state'
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'product_weight': forms.Select(attrs={'class': 'form-control'}),  # Use Select widget for choices
            'product_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter product value'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'pickup_state': forms.Select(attrs={'class': 'form-control'}),
            'destination_state': forms.Select(attrs={'class': 'form-control'}),
        }


class TruckApprovalForm(forms.Form):
    truck_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    tracker_id = forms.CharField(
        max_length=255,
        required=True,
        label="Tracker ID",
        help_text="Enter the tracker ID to assign to the approved trucks.",
    )

    def __init__(self, *args, **kwargs):
        super(TruckApprovalForm, self).__init__(*args, **kwargs)
        self.fields['truck_ids'].choices = [
            (truck.id, f'{truck.name} - Owned by {truck.owner.username}') 
            for truck in Truck.objects.filter(available=False)
        ]


class AdminBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'truck', 'product_name', 'product_weight', 'product_value', 
            'phone_number', 'pickup_state', 'destination_state', 'client'
        ]
        widgets = {
            'truck': forms.Select(attrs={'class': 'form-control'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'product_weight': forms.Select(attrs={'class': 'form-control'}),
            'product_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter product value'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'pickup_state': forms.Select(attrs={'class': 'form-control'}),
            'destination_state': forms.Select(attrs={'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-control'}),
        }# forms.py
class AdminBookingForm(forms.ModelForm):
    delivery_cost = forms.DecimalField(
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter delivery cost'
        })
    )
    
    class Meta:
        model = Booking
        fields = [
            'truck', 'client', 'product_name', 'product_weight', 
            'product_value', 'phone_number', 'pickup_state', 
            'destination_state', 'delivery_cost'
        ]
        widgets = {
            'truck': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Choose a truck'}),
            'client': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Choose a client'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
            'product_weight': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Pick a weight'}),
            'product_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter product value'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'pickup_state': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Select a pickup state'}),
            'destination_state': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Select a destination state'}),
        }
