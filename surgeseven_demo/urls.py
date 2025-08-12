# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static
# from django.shortcuts import redirect
# from core.views import handler400, handler403, handler404, handler500

# handler400 = 'core.views.handler400'
# handler403 = 'core.views.handler403'
# handler404 = 'core.views.handler404'
# handler500 = 'core.views.handler500'

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('dashboard.urls')),
#     path('accounts/', include('users.urls')),
#     path('subscription/', include('subscriptions.urls')),
#     path('booking/', include('booking.urls')),
#     path('payment/', include('payment.urls')),
#     path('delivery/', include('delivery.urls')),
#     path('notify/', include('notifications.urls')),
#     path('tracker/', include('tracker.urls')),

#     # Redirect root URL to the login page
#     path('', lambda request: redirect('login')),  # Replace 'login' with your actual login URL name
# ]

# urlpatterns = urlpatterns+static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)





from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from dashboard.views import GuestHomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', GuestHomeView.as_view(), name='home'),
    path('dashboard/', include('dashboard.urls')),  # Add prefix
    path('accounts/', include('users.urls')),
    path('subscription/', include('subscriptions.urls')),
    path('booking/', include('booking.urls')),
    path('payment/', include('payment.urls')),
    path('delivery/', include('delivery.urls')),
    path('notify/', include('notifications.urls')),
    path('tracker/', include('tracker.urls')),

    # Root redirect - must be last in this section
    # path('', RedirectView.as_view(url='guest/home/', permanent=False)),
]

# Media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Error handlers - MUST BE AT THE BOTTOM
handler400 = 'core.views.handler400'
handler403 = 'core.views.handler403'
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'


