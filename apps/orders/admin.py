from django.contrib import admin
from .models import Coupon, Cart, CartItem, Order, OrderItem, OrderStatusHistory, Review

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_order_value', 'is_active', 'used_count')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('item_name', 'price', 'quantity', 'subtotal')

class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('from_status', 'to_status', 'changed_by_user', 'changed_by_role', 'notes', 'created_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'restaurant', 'customer', 'status', 'total_amount', 'payment_method', 'payment_status', 'placed_at')
    list_filter = ('status', 'payment_method', 'payment_status', 'placed_at')
    search_fields = ('order_number', 'customer__email', 'restaurant__name')
    readonly_fields = ('order_number', 'placed_at', 'pickup_otp', 'delivery_otp')
    inlines = [OrderItemInline, OrderStatusHistoryInline]

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('order', 'restaurant', 'customer', 'rating', 'created_at')
    list_filter = ('rating', 'restaurant')

