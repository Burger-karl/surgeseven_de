# qr_generator/urls.py
from django.urls import path
from . import views

app_name = 'qr_generator'

urlpatterns = [
    path('', views.QRCodeListView.as_view(), name='list'),
    path('create/', views.QRCodeCreateView.as_view(), name='create'),
    path('<int:pk>/', views.QRCodeDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.QRCodeUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.QRCodeDeleteView.as_view(), name='delete'),
    path('redirect/<slug:slug>/', views.QRCodeRedirectView.as_view(), name='redirect'),
    path('download/<slug:slug>/', views.QRCodeDownloadView.as_view(), name='download'),
    path('api/<slug:slug>/', views.QRCodeAPIView.as_view(), name='api'),
]