from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('dashboard/', views.delivery_dashboard_view, name='dashboard'),
    path('api/toggle-online/', views.ToggleOnlineStatusAPI.as_view(), name='api_toggle_online'),
    path('api/update-location/', views.UpdateLocationAPI.as_view(), name='api_update_location'),
    path('api/available-orders/', views.AvailableOrdersAPI.as_view(), name='api_available_orders'),
    path('api/orders/<uuid:order_id>/accept/', views.AcceptOrderAPI.as_view(), name='api_accept_order'),
    path('api/orders/<uuid:order_id>/verify-pickup/', views.VerifyPickupOTPAPI.as_view(), name='api_verify_pickup'),
    path('api/orders/<uuid:order_id>/verify-delivery/', views.VerifyDeliveryOTPAPI.as_view(), name='api_verify_delivery'),
]

