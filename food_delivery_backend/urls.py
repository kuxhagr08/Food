from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('django-admin/', admin.site.urls), # Admin site URL
    path('admin/', RedirectView.as_view(url='/django-admin/', permanent=False)), # Redirect /admin/ to /django-admin/
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('restaurants/', include('apps.restaurants.urls', namespace='restaurants')),
    path('orders/', include('apps.orders.urls', namespace='orders')),
    path('delivery/', include('apps.delivery.urls', namespace='delivery')),
    path('kitchen/', include('apps.kitchen.urls', namespace='kitchen')),
    path('cms/', include('apps.cms.urls', namespace='cms')),
    path('payments/', include('apps.payments.urls', namespace='payments')),
    path('', include('apps.core.urls', namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
