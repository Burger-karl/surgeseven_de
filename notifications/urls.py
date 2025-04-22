from django.urls import path
from .views import NotificationDetailView, mark_all_notifications_as_read, AllNotificationsListView

urlpatterns = [
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification_detail'),
    path('mark-all-as-read/', mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
    path('all/', AllNotificationsListView.as_view(), name='all_notifications'),   
]   