# import requests

# class PaystackClient:
#     def __init__(self):
#         self.secret_key = 'sk_test_578e98623123672928132bb40df9ec97f9631cda'
#         self.base_url = 'https://api.paystack.co'

#     def initialize_transaction(self, email, amount, reference, callback_url):
#         url = f'{self.base_url}/transaction/initialize'
#         headers = {
#             'Authorization': f'Bearer {self.secret_key}',
#             'Content-Type': 'application/json',
#         }
#         data = {
#             'email': email,
#             'amount': amount,
#             'reference': reference,
#             'callback_url': callback_url,
#         }
#         response = requests.post(url, headers=headers, json=data)
#         return response.json()

#     def verify_transaction(self, reference):
#         url = f'{self.base_url}/transaction/verify/{reference}'
#         headers = {
#             'Authorization': f'Bearer {self.secret_key}',
#         }
#         response = requests.get(url, headers=headers)
#         return response.json()



# paystack_client.py
import requests
import os
from django.conf import settings

class PaystackClient:
    def __init__(self):
        # Use environment variable for secret key
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.base_url = 'https://api.paystack.co'
        
        # Validate that we have a secret key
        if not self.secret_key:
            raise ValueError("Paystack secret key not configured")

    def initialize_transaction(self, email, amount, reference, callback_url):
        url = f'{self.base_url}/transaction/initialize'
        headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }
        data = {
            'email': email,
            'amount': amount,
            'reference': reference,
            'callback_url': callback_url,
            'metadata': {
                'custom_fields': [
                    {
                        'display_name': "Paid Via",
                        'variable_name': "paid_via",
                        'value': "SurgeSeven Platform"
                    }
                ]
            }
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Log the error and return a consistent error format
            return {
                'status': False,
                'message': f'Payment initialization failed: {str(e)}'
            }

    def verify_transaction(self, reference):
        url = f'{self.base_url}/transaction/verify/{reference}'
        headers = {
            'Authorization': f'Bearer {self.secret_key}',
        }
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': False,
                'message': f'Payment verification failed: {str(e)}'
            }