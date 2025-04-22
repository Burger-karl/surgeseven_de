from django.urls import path
from .views import ClientDashboardView, TruckOwnerDashboardView, AboutView, ClientHomeView, TruckOwnerHomeView, AdminHomeView

urlpatterns = [
    path('client/home/', ClientHomeView.as_view(), name='client_home'),
    path('truck-owner/home/', TruckOwnerHomeView.as_view(), name='truck_owner_home'),
    path('home/', AdminHomeView.as_view(), name='admin_home'),
    path('about/', AboutView.as_view(), name='about'),
    
    path('client-dashboard/', ClientDashboardView.as_view(), name='client_dashboard'),
    path('truck-owner-dashboard/', TruckOwnerDashboardView.as_view(), name='truck_owner_dashboard'),
]
