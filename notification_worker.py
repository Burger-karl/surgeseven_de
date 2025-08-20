import os
import time
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surgeseven_demo.settings')
django.setup()

def main():
    print("Starting notification worker...")
    while True:
        try:
            print("Checking for unsent notifications...")
            call_command('send_push_notifications')
        except Exception as e:
            print(f"Error sending notifications: {e}")
        
        # Sleep for 5 minutes (300 seconds)
        time.sleep(300)

if __name__ == "__main__":
    main()