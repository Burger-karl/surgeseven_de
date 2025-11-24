from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from dashboard.views import GuestHomeView
from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.views.generic.base import TemplateView

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return ['home', 'about', 'available_trucks', 'subscription-plans']

    def location(self, item):
        return reverse(item)

# Define sitemaps dictionary
sitemaps = {
    'static': StaticViewSitemap,
}


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
    path('webpush/', include('webpush.urls')),
    path('qr-codes/', include('qr_generator.urls')),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(
        template_name="robots.txt", 
        content_type="text/plain")
    ),

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


