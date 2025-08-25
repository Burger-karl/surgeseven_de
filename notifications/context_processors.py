from .models import Notification
from django.conf import settings

def notifications(request):
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(user=request.user, read=False).count()
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]  # Show latest 5 notifications
        return {
            'unread_notifications_count': unread_notifications_count,
            'notifications': notifications,
        }
    return {}

def vapid_public_key(request):
    return {
        'VAPID_PUBLIC_KEY': settings.WEBPUSH_SETTINGS.get('VAPID_PUBLIC_KEY', '')
    }