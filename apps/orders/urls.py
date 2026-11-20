from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('history/', views.OrderHistoryView.as_view(), name='history'),
    path('<uuid:order_id>/tracking/', views.LiveOrderTrackingView.as_view(), name='live_tracking'),

    # APIs
    path('api/cart/add/', views.AddToCartAPI.as_view(), name='api_cart_add'),
    path('api/cart/update/', views.UpdateCartItemAPI.as_view(), name='api_cart_update'),
    path('api/cart/apply-coupon/', views.ApplyCouponAPI.as_view(), name='api_apply_coupon'),
    path('api/place-order/', views.PlaceOrderAPI.as_view(), name='api_place_order'),
    path('api/<uuid:order_id>/cancel/', views.CancelOrderAPI.as_view(), name='api_cancel_order'),
    path('api/<uuid:order_id>/review/', views.ReviewSubmitAPI.as_view(), name='api_review'),
]

