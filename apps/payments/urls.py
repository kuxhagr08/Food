from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('mock-gateway/<uuid:order_id>/', views.MockPaymentGatewayView.as_view(), name='mock_gateway'),
]

