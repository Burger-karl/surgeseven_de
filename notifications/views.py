from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView
from django.contrib import messages
from .models import Notification

class NotificationDetailView(DetailView):
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'

    def get_object(self):
        return get_object_or_404(Notification, id=self.kwargs['pk'], user=self.request.user)

    def get(self, request, *args, **kwargs):
        # Get the notification
        notification = self.get_object()
        
        # Render the notification detail page
        response = super().get(request, *args, **kwargs)
        
        # Delete the notification after rendering the page
        notification.delete()
        messages.success(request, "Notification has been removed.")
        
        return response


def mark_all_notifications_as_read(request):
    if request.user.is_authenticated:
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect('about')


class AllNotificationsListView(ListView):
    model = Notification
    template_name = 'notifications/all_notifications.html'
    context_object_name = 'notifications'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    