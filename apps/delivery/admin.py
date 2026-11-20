from django.contrib import admin
from .models import DeliveryAssignment, DeliveryLocationLog

@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'delivery_partner', 'status', 'partner_earnings', 'accepted_at', 'delivered_at')
    list_filter = ('status', 'accepted_at')
    search_fields = ('order__order_number', 'delivery_partner__email')

@admin.register(DeliveryLocationLog)
class DeliveryLocationLogAdmin(admin.ModelAdmin):
    list_display = ('delivery_partner', 'order', 'latitude', 'longitude', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('delivery_partner__email', 'order__order_number')

