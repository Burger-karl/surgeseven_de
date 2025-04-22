from django.urls import path
from .views import SubscriptionPlanListView, UserSubscriptionsView, SubscribeView, PaymentCallbackView, CancelSubscriptionView

urlpatterns = [
    path('subscription-plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path('user-subscriptions/', UserSubscriptionsView.as_view(), name='user-subscriptions'),
    path('subscribe/<int:pk>/', SubscribeView.as_view(), name='subscribe'),
    path('payment-callback/<int:subscription_id>/', PaymentCallbackView.as_view(), name='payment-callback'),

    path('cancel-subscription/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
]

