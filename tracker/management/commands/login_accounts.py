# tracker/management/commands/login_itracksafex_admin.py

import hashlib
import requests
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Login to iTrackSafeX admin account and retrieve token"

    def handle(self, *args, **kwargs):
        username = "Surge Seven"
        password = "Surge#7"
        login_url = "https://www.itracksafe.com/webapi?action=login"  # Replace with actual domain

        # Password must be MD5 (32 lowercase)
        encrypted_password = hashlib.md5(password.encode()).hexdigest()

        payload = {
            "type": "USER",
            "from": "WEB",
            "username": username,
            "password": encrypted_password,
            "browser": "Django/management"
        }

        try:
            response = requests.post(login_url, json=payload)
            result = response.json()

            if result.get("state") == 0:
                token = result.get("token")
                self.stdout.write(self.style.SUCCESS(f"✅ Login successful!\n🔐 Token: {token}"))
            else:
                cause = result.get("caus", "Unknown error")
                self.stdout.write(self.style.ERROR(f"❌ Login failed: {cause}"))

        except Exception as e:
            self.stderr.write(f"❌ Error during login: {str(e)}")
