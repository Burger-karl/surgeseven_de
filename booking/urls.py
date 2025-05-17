from django.urls import path
from .views import (
    TruckCreateView, TruckListView, BookingCreateView, BookingListView, AvailableTruckListView,
    GenerateReceiptView, BookingUpdateView, AdminBookingCreateView, InsuranceReceiptView,
    AdminTruckListView, AdminTruckDetailView, BookingWithUpdatedCostView, BookingAdminListView,
)

urlpatterns = [
    path('trucks/create/', TruckCreateView.as_view(), name='truck_create'),
    path('trucks/', TruckListView.as_view(), name='truck_list'),
    path('bookings/create/<int:truck_id>/', BookingCreateView.as_view(), name='booking-create'),
    path('bookings/', BookingListView.as_view(), name='booking_list'),
    path('edit/<int:pk>/', BookingUpdateView.as_view(), name='booking_edit'),
    path('available-trucks/', AvailableTruckListView.as_view(), name='available_trucks'),
    path('bookings/receipt/<str:booking_code>/', GenerateReceiptView.as_view(), name='generate_receipt'),
    path('insurance-receipt/<str:booking_code>/', InsuranceReceiptView.as_view(), name='insurance_receipt'),
    

    # Admin routes
    path('admin/trucks/', AdminTruckListView.as_view(), name='admin_truck_list'),
    path('admin/trucks/<int:pk>/', AdminTruckDetailView.as_view(), name='admin_truck_detail'),
    path('admin/bookings/', BookingAdminListView.as_view(), name='admin-booking-list'),
    path('bookings/updated-cost/', BookingWithUpdatedCostView.as_view(), name='updated_cost_booking_list'),
    path('admin/create/', AdminBookingCreateView.as_view(), name='admin_booking_create'),
]
