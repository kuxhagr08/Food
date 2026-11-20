import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from apps.orders.models import Order

class DeliveryAssignment(BaseModel):
    STATUS_CHOICES = (
        ('ASSIGNED', 'Assigned'),
        ('PICKED_UP', 'Picked Up'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery_assignment')
    delivery_partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_assignments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ASSIGNED')
    partner_earnings = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('45.00'))
    distance_km = models.FloatField(default=0.0)
    accepted_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-accepted_at']

    def __str__(self):
        return f"Assignment for {self.order.order_number} to {self.delivery_partner.email}"


class DeliveryLocationLog(BaseModel):
    delivery_partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='location_logs')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='partner_locations')
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.delivery_partner.email} at ({self.latitude}, {self.longitude})"

