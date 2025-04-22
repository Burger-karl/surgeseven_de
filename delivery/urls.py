from django.urls import path
from delivery.views import ActiveDeliveryView, DeliveryHistoryView, AdminDeliveryScheduleListView, UpdateDeliveryScheduleStatusView

urlpatterns = [
    path('active-deliveries/', ActiveDeliveryView.as_view(), name='active_deliveries'),
    path('delivery-history/', DeliveryHistoryView.as_view(), name='delivery_history'),

    path('admin/delivery-schedules/', AdminDeliveryScheduleListView.as_view(), name='admin_delivery_schedule_list'),
    path('admin/delivery-schedules/<int:pk>/update/', UpdateDeliveryScheduleStatusView.as_view(), name='update_delivery_status'),
]
