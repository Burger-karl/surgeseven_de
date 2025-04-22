# from django.core.management.base import BaseCommand
# from tracker.services import create_tracker_account
# from hashlib import md5

# class Command(BaseCommand):
#     help = 'Creates accounts in the tracker API'

#     def handle(self, *args, **kwargs):
#         # Create Admin Account
#         admin_username = "admin_surgeseven"
#         admin_password = md5("admin123".encode()).hexdigest()  # MD5 hash of the password
#         create_tracker_account(admin_username, admin_password, usertype=1)
#         self.stdout.write(self.style.SUCCESS(f'Successfully created admin account: {admin_username}'))

#         # Create Truck Owner Account
#         truck_owner_username = "truckowner1"
#         truck_owner_password = md5("owner123".encode()).hexdigest()
#         create_tracker_account(truck_owner_username, truck_owner_password, usertype=11)
#         self.stdout.write(self.style.SUCCESS(f'Successfully created truck owner account: {truck_owner_username}'))

#         # Create Client Account
#         client_username = "client1"
#         client_password = md5("client123".encode()).hexdigest()
#         create_tracker_account(client_username, client_password, usertype=11)
#         self.stdout.write(self.style.SUCCESS(f'Successfully created client account: {client_username}'))



















# tracker/management/commands/create_itracksafex_accounts.py

import hashlib
import json
import requests
from django.core.management.base import BaseCommand

ITRACKSAFE_URL = "https://itracksafe.com/webapi?action=adduser"
CREATOR = "superadmin_username_here"
TOKEN = "your_api_token_here"

ACCOUNTS = [
    {"username": "admin_user", "password": "admin12345", "usertype": 1},         # System Administrator
    {"username": "client_user", "password": "client12345", "usertype": 11},      # Ordinary monitor
    {"username": "truck_owner_user", "password": "truck12345", "usertype": 11},  # Ordinary monitor
]

class Command(BaseCommand):
    help = "Create iTrackSafeX accounts for admin, client, and truck owner"

    def handle(self, *args, **kwargs):
        for account in ACCOUNTS:
            encrypted_password = hashlib.md5(account["password"].encode()).hexdigest()

            payload = {
                "creator": CREATOR,
                "username": account["username"],
                "password": encrypted_password,
                "usertype": account["usertype"],
                "multilogin": 1
            }

            try:
                response = requests.post(ITRACKSAFE_URL + f"&token={TOKEN}", json=payload)
                result = response.json()

                if result.get("status") == 0:
                    self.stdout.write(self.style.SUCCESS(f"✅ Created user: {account['username']}"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️ Failed to create {account['username']}: {result.get('cause')}"))

            except Exception as e:
                self.stderr.write(f"❌ Error creating {account['username']}: {str(e)}")
