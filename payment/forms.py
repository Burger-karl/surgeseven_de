from django import forms
from .models import WithdrawalMethod

# forms.py
BANK_CODES = (
    ("044", "Access Bank"),
    ("063", "Diamond Bank"),
    ("011", "First Bank of Nigeria"),
    ("057", "Zenith Bank"),
    ("068", "Standard Chartered Bank"),
    ("070", "Fidelity Bank"),
    ("023", "CitiBank"),
    ("215", "Unity Bank"),
    ("301", "JAIZ Bank"),
    ("050", "Ecobank Plc"),
    ("221", "Stanbic IBTC Bank"),
    ("035", "Wema Bank"),
    ("084", "Enterprise Bank"),
    ("033", "United Bank for Africa"),
    ("100", "SunTrust Bank"),
    ("030", "Heritage"),
    ("058", "GTBank Plc"),
    ("232", "Sterling Bank"),
    ("032", "Union Bank"),
    ("082", "Keystone Bank"),
    ("076", "Skye Bank"),
    ("214", "First City Monument Bank")

    # Add all Nigerian banks from Flutterwave's API
)

class WithdrawalMethodForm(forms.ModelForm):
    bank_code = forms.ChoiceField(choices=BANK_CODES)
    account_number = forms.CharField(max_length=20)
    account_name = forms.CharField(max_length=100)

    class Meta:
        model = WithdrawalMethod
        fields = ['bank_code', 'account_number', 'account_name']

    def save(self, commit=True):
        method = super().save(commit=False)
        method.details = {
            'bank_code': self.cleaned_data['bank_code'],
            'account_number': self.cleaned_data['account_number'],
            'account_name': self.cleaned_data['account_name']
        }
        if commit:
            method.save()
        return method        

class WithdrawalRequestForm(forms.Form):
    amount = forms.DecimalField(
        min_value=10.00,  # Minimum withdrawal amount
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    method = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['method'].queryset = WithdrawalMethod.objects.filter(user=user, is_verified=True)