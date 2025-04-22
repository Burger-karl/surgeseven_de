from django.urls import path
from . import views


urlpatterns = [
    path('subscription/<int:plan_id>/', views.create_subscription_payment, name='create-subscription-payment'),
    path('verify-payment/<str:ref>/', views.verify_payment, name='verify-payment'),
    
    path('booking/payment/<int:booking_id>/', views.CreateBookingPaymentView.as_view(), name='create-booking-payment'),
    path('booking/payment/verify/<str:ref>/', views.VerifyBookingPaymentView.as_view(), name='verify-booking-payment'),
]
