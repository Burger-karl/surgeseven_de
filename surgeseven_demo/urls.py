from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('users.urls')),
    path('subscription/', include('subscriptions.urls')),
    path('booking/', include('booking.urls')),
    path('payment/', include('payment.urls')),
    path('delivery/', include('delivery.urls')),
    path('notify/', include('notifications.urls')),
    # path('tracker/', include('tracker.urls')),

    # Redirect root URL to the login page
    path('', lambda request: redirect('login')),  # Replace 'login' with your actual login URL name
]

urlpatterns = urlpatterns+static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)


