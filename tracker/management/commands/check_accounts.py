# tracker/management/commands/check_tracker_accounts.py
from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from hashlib import md5
import json

ITRACKSAFEX_API_URL = "https://itracksafe.com/webapi"

class Command(BaseCommand):
    help = 'Check if accounts exist in the tracker API and verify login capability'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Check a specific username instead of all configured accounts'
        )

    def handle(self, *args, **options):
        # Define the accounts to check
        ACCOUNTS = [
            {
                "username": "admin_surgeseven",
                "password": "admin123",
                "role": "admin"
            },
            {
                "username": "truckowner1",
                "password": "owner123",
                "role": "truck_owner"
            },
            {
                "username": "client1",
                "password": "client123",
                "role": "client"
            }
        ]

        # If a specific username is provided, filter the accounts
        if options['username']:
            ACCOUNTS = [acc for acc in ACCOUNTS if acc['username'] == options['username']]
            if not ACCOUNTS:
                self.stdout.write(self.style.ERROR(f"No configured account with username: {options['username']}"))
                return

        self.stdout.write(self.style.MIGRATE_HEADING("Starting tracker account verification..."))

        for account in ACCOUNTS:
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"Checking account: {account['username']} ({account['role']})")
            self.stdout.write("="*50)

            # 1. Check account existence
            existence = self.check_account_existence(account['username'])
            self.print_result("Account Existence Check", existence)

            # 2. Verify login capability
            login_status = self.verify_login(account['username'], account['password'])
            self.print_result("Login Verification", login_status)

    def check_account_existence(self, username):
        """Check if account exists in tracker API"""
        payload = {
            "action": "getuserinfo",
            "username": username
        }
        
        try:
            response = requests.post(
                ITRACKSAFEX_API_URL,
                json=payload,
                timeout=10
            )
            data = response.json()
            
            if response.status_code == 200:
                if data.get("status") == 0:  # Success status code may vary by API
                    return {
                        "exists": True,
                        "data": data,
                        "status_code": response.status_code
                    }
                return {
                    "exists": False,
                    "error": data.get("message", "Account not found"),
                    "status_code": response.status_code
                }
            return {
                "exists": False,
                "error": f"HTTP {response.status_code}",
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "exists": False,
                "error": str(e),
                "status_code": None
            }

    def verify_login(self, username, password):
        """Verify login capability"""
        hashed_pw = md5(password.encode()).hexdigest()
        payload = {
            "action": "login",
            "username": username,
            "password": hashed_pw
        }
        
        try:
            response = requests.post(
                ITRACKSAFEX_API_URL,
                json=payload,
                timeout=10
            )
            data = response.json()
            
            if response.status_code == 200:
                if data.get("token"):
                    return {
                        "can_login": True,
                        "token": data["token"][:15] + "...",  # Show partial token for security
                        "status_code": response.status_code
                    }
                return {
                    "can_login": False,
                    "error": data.get("message", "No token in response"),
                    "status_code": response.status_code
                }
            return {
                "can_login": False,
                "error": f"HTTP {response.status_code}",
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "can_login": False,
                "error": str(e),
                "status_code": None
            }

    def print_result(self, title, result):
        """Helper to print consistent result output"""
        self.stdout.write(f"\n{title}:")
        
        if "error" in result:
            self.stdout.write(self.style.ERROR(f"❌ Error: {result['error']}"))
        elif result.get("exists", False) or result.get("can_login", False):
            self.stdout.write(self.style.SUCCESS("✅ Success"))
            for key, value in result.items():
                if key not in ["exists", "can_login"]:
                    self.stdout.write(f"  {key}: {value}")
        else:
            self.stdout.write(self.style.WARNING("⚠️ Failed"))
            for key, value in result.items():
                if key not in ["exists", "can_login"]:
                    self.stdout.write(f"  {key}: {value}")