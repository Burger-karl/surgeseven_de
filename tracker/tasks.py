from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from tracker.models import TrackerToken
from tracker.services import TrackerAccountService

@shared_task
def refresh_tracker_tokens():
    """Refresh all tracker tokens that are about to expire"""
    service = TrackerAccountService()
    # Get tokens that were updated more than 23 hours ago
    expired_tokens = TrackerToken.objects.filter(
        updated_at__lt=timezone.now() - timedelta(hours=23)
    )
    
    for token in expired_tokens:
        service.login(token.user.username, token.user.tracker_password)