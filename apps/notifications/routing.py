from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/orders/(?P<order_id>[0-9a-f-]+)/$', consumers.OrderTrackingConsumer.as_asgi()),
    re_path(r'^ws/kitchen/(?P<restaurant_id>[0-9a-f-]+)/$', consumers.KitchenKdsConsumer.as_asgi()),
    re_path(r'^ws/delivery/$', consumers.DeliveryPartnerConsumer.as_asgi()),
    re_path(r'^ws/admin-dashboard/$', consumers.AdminConsumer.as_asgi()),
]

