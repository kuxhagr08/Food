from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'amount', 'gateway', 'status', 'created_at')
    list_filter = ('status', 'gateway', 'created_at')
    search_fields = ('transaction_id', 'order__order_number')
    readonly_fields = ('transaction_id', 'order', 'amount', 'gateway', 'status', 'raw_response', 'created_at')

