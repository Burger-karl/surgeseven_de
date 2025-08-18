# notifications/management/commands/send_push_notifications.py
from django.core.management.base import BaseCommand
from notifications.models import Notification
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sends push notifications for unsent notifications'
    
    def handle(self, *args, **options):
        try:
            # Get notifications from the last 24 hours that haven't been sent
            notifications = Notification.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24),
                push_sent=False
            )
            
            sent_count = 0
            for notification in notifications:
                try:
                    # Trigger the signal to send the push notification
                    notification.save()
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification {notification.id}: {str(e)}")
            
            logger.info(f"Successfully sent {sent_count} push notifications")
            self.stdout.write(self.style.SUCCESS(f'Sent push notifications for {sent_count} notifications'))
        except Exception as e:
            logger.error(f"Notification worker failed: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))