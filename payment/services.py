import uuid
import requests
from django.conf import settings
from django.core.exceptions import ValidationError

FLUTTERWAVE_URL = "https://api.flutterwave.com/v3"

def initiate_flutterwave_payout(account_bank, account_number, amount, narration, recipient_name):
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "account_bank": account_bank,  # e.g., "044" for Access Bank Nigeria
        "account_number": account_number,
        "amount": amount,
        "narration": narration,
        "currency": "NGN",
        "reference": f"WDR_{uuid.uuid4().hex[:10]}",
        "beneficiary_name": recipient_name
    }

    try:
        response = requests.post(
            f"{FLUTTERWAVE_URL}/transfers",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ValidationError(f"Flutterwave payout failed: {str(e)}")