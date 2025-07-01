from django.urls import path
from . import views


urlpatterns = [
    path('subscription/<int:plan_id>/', views.create_subscription_payment, name='create-subscription-payment'),
    path('verify-payment/<str:ref>/', views.verify_payment, name='verify-payment'),
    
    path('booking/payment/<int:booking_id>/', views.CreateBookingPaymentView.as_view(), name='create-booking-payment'),
    path('booking/payment/verify/<str:ref>/', views.VerifyBookingPaymentView.as_view(), name='verify-booking-payment'),

    # WITHDRAWAL
    path('withdraw/', views.WithdrawalView.as_view(), name='withdraw'),
    path('withdraw/method/add/', views.add_withdrawal_method, name='add_withdrawal_method'),
    path('withdraw/history/', views.withdrawal_history, name='withdrawal_history'),
    
    # Admin URLs
    path('admin/withdrawals/', views.process_withdrawals, name='process_withdrawals'),
    path('admin/withdrawals/<int:withdrawal_id>/', views.update_withdrawal_status, name='update_withdrawal_status'),
]

