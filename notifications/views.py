from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView
from django.contrib import messages
from .models import Notification

# class NotificationDetailView(DetailView):
#     model = Notification
#     template_name = 'notifications/notification_detail.html'
#     context_object_name = 'notification'

#     def get_object(self):
#         return get_object_or_404(Notification, id=self.kwargs['pk'], user=self.request.user)

#     def get(self, request, *args, **kwargs):
#         # Get the notification
#         notification = self.get_object()
        
#         # Render the notification detail page
#         response = super().get(request, *args, **kwargs)
        
#         # Delete the notification after rendering the page
#         notification.delete()
#         messages.success(request, "Notification has been removed.")
        
#         return response


class NotificationDetailView(DetailView):
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'

    def get_object(self):
        return get_object_or_404(Notification, id=self.kwargs['pk'], user=self.request.user)

    def get(self, request, *args, **kwargs):
        # Mark notification as read
        notification = self.get_object()
        notification.read = True
        notification.save()
        return super().get(request, *args, **kwargs)


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
    

# notifications/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
import json
from .models import PushSubscription

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class PushSubscriptionView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            subscription = PushSubscription.objects.create(
                user=request.user,
                endpoint=data['endpoint'],
                auth=data['keys']['auth'],
                p256dh=data['keys']['p256dh']
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    def delete(self, request):
        try:
            data = json.loads(request.body)
            PushSubscription.objects.filter(
                user=request.user,
                endpoint=data['endpoint']
            ).delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        

# views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import PushSubscription

@csrf_exempt
@require_POST
@login_required
def push_subscribe(request):
    try:
        # Parse the subscription data from the request
        data = json.loads(request.body)
        print("Received data:", data)  # Debug print
        
        # Extract data from dictionary (not as attributes)
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        
        # Extract auth and p256dh from keys dictionary
        auth = keys.get('auth', '')
        p256dh = keys.get('p256dh', '')
        
        if not endpoint:
            return JsonResponse({'status': 'error', 'message': 'Missing endpoint'}, status=400)
        
        # Save the subscription to the database
        subscription, created = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={'auth': auth, 'p256dh': p256dh}
        )
        
        if created:
            message = 'Subscription created successfully'
        else:
            message = 'Subscription updated successfully'
        
        return JsonResponse({'status': 'success', 'message': message})
    except Exception as e:
        print("Error:", str(e))  # Debug print
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    