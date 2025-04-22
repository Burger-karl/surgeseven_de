import requests

class PaystackClient:
    def __init__(self):
        self.secret_key = 'sk_test_578e98623123672928132bb40df9ec97f9631cda'
        self.base_url = 'https://api.paystack.co'

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
        }
        response = requests.post(url, headers=headers, json=data)
        return response.json()

    def verify_transaction(self, reference):
        url = f'{self.base_url}/transaction/verify/{reference}'
        headers = {
            'Authorization': f'Bearer {self.secret_key}',
        }
        response = requests.get(url, headers=headers)
        return response.json()
