from django.conf import settings
import os
from django import forms
from .models import Truck, Booking, TruckImage
from django.core.exceptions import ValidationError


class TruckForm(forms.ModelForm):
    class Meta:
        model = Truck
        fields = ['name', 'weight_range', 'state', 'local_government']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter truck name'}),
            'weight_range': forms.Select(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
            'local_government': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter local government'}),
        }


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result
    

class TruckImageForm(forms.ModelForm):
    images = MultipleFileField(
        label='Upload 3 Images of the Truck',
        help_text='Please upload exactly 3 images (max 5MB each) showing different angles of the truck.',
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*'
        })
    )
    
    class Meta:
        model = TruckImage
        fields = []
        
    def clean_images(self):
        images = self.files.getlist('images')
        
        # Validate exactly 3 images
        if len(images) != 3:
            raise ValidationError("Exactly 3 images must be uploaded.")
        
        # Validate each image
        for image in images:
            if not image.content_type.startswith('image/'):
                raise ValidationError(
                    f"File {image.name} is not an image. Only image files are allowed."
                )
                
            # Check file extension
            ext = os.path.splitext(image.name)[1].lower()
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            if ext not in valid_extensions:
                raise ValidationError(
                    f"Unsupported file extension: {ext}. Supported formats: {', '.join(valid_extensions)}"
                )
            
            # Check file size (5MB limit)
            max_size = getattr(settings, 'MAX_IMAGE_UPLOAD_SIZE', 5 * 1024 * 1024)  # 5MB default
            if image.size > max_size:
                raise ValidationError(
                    f"File {image.name} is too large. Maximum size is {max_size/1024/1024}MB."
                )
                
        return images
                


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


# class TruckApprovalForm(forms.Form):
#     truck_ids = forms.MultipleChoiceField(
#         widget=forms.CheckboxSelectMultiple,
#         required=False
#     )
#     tracker_id = forms.CharField(
#         max_length=255,
#         required=True,
#         label="Tracker ID",
#         help_text="Enter the tracker ID to assign to the approved trucks.",
#     )

#     def __init__(self, *args, **kwargs):
#         super(TruckApprovalForm, self).__init__(*args, **kwargs)
#         self.fields['truck_ids'].choices = [
#             (truck.id, f'{truck.name} - Owned by {truck.owner.username}') 
#             for truck in Truck.objects.filter(available=False)
#         ]



# booking/forms.py - Update TruckApprovalForm and add new forms

from django import forms
from .models import Truck, Booking, TruckImage
from django.core.exceptions import ValidationError

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
    activate_trucks = forms.BooleanField(
        required=False,
        initial=True,
        label="Activate selected trucks",
        help_text="Also activate the trucks while approving"
    )

    def __init__(self, *args, **kwargs):
        super(TruckApprovalForm, self).__init__(*args, **kwargs)
        # Show both activated and non-activated trucks that are not available
        self.fields['truck_ids'].choices = [
            (truck.id, f'{truck.name} - Owned by {truck.owner.username} (Activated: {truck.activated})') 
            for truck in Truck.objects.filter(available=False)
        ]

class TruckActivationForm(forms.Form):
    truck_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select trucks to activate"
    )
    tracker_id = forms.CharField(
        max_length=255,
        required=False,
        label="Tracker ID (Optional)",
        help_text="Assign tracker ID to activated trucks. Leave blank to set later.",
    )

    def __init__(self, *args, **kwargs):
        super(TruckActivationForm, self).__init__(*args, **kwargs)
        # Show only trucks that can be activated (not activated yet and meet criteria)
        activatable_trucks = []
        for truck in Truck.objects.filter(activated=False):
            if truck.can_be_activated():
                activatable_trucks.append(
                    (truck.id, f'{truck.name} - {truck.owner.username} ({truck.get_weight_range_display()})')
                )
        self.fields['truck_ids'].choices = activatable_trucks

class TruckDeactivationForm(forms.Form):
    truck_ids = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select trucks to deactivate"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label="Reason for deactivation",
        help_text="Optional: Provide reason for deactivation"
    )

    def __init__(self, *args, **kwargs):
        super(TruckDeactivationForm, self).__init__(*args, **kwargs)
        # Show only activated trucks
        self.fields['truck_ids'].choices = [
            (truck.id, f'{truck.name} - {truck.owner.username} (Tracker: {truck.tracker_id or "Not assigned"})') 
            for truck in Truck.objects.filter(activated=True)
        ]


class TruckEditForm(forms.ModelForm):
    class Meta:
        model = Truck
        fields = [
            'name', 'weight_range', 'available', 'state', 
            'local_government', 'tracker_id', 'activated'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'weight_range': forms.Select(attrs={'class': 'form-select'}),
            'state': forms.Select(attrs={'class': 'form-select'}),
            'local_government': forms.TextInput(attrs={'class': 'form-control'}),
            'tracker_id': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_tracker_id(self):
        tracker_id = self.cleaned_data['tracker_id']
        if tracker_id:
            # Ensure tracker ID is unique except for blank values
            qs = Truck.objects.filter(tracker_id=tracker_id)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This tracker ID is already in use.")
        return tracker_id


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
