from django.urls import path
from . import views

app_name = 'kitchen'

urlpatterns = [
    path('dashboard/', views.kitchen_dashboard_view, name='dashboard'),
    path('api/orders/', views.KitchenOrdersDataAPI.as_view(), name='api_orders'),
    path('api/orders/<uuid:order_id>/accept/', views.AcceptKitchenOrderAPI.as_view(), name='api_accept'),
    path('api/orders/<uuid:order_id>/reject/', views.RejectKitchenOrderAPI.as_view(), name='api_reject'),
    path('api/orders/<uuid:order_id>/preparing/', views.MarkPreparingAPI.as_view(), name='api_preparing'),
    path('api/orders/<uuid:order_id>/ready/', views.MarkReadyAPI.as_view(), name='api_ready'),
]

