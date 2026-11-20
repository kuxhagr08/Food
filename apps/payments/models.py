import uuid
from django.db import models
from apps.core.models import BaseModel
from apps.orders.models import Order

class Payment(BaseModel):
    GATEWAY_CHOICES = (
        ('MOCK', 'Mock Gateway'),
        ('RAZORPAY', 'Razorpay Test Mode'),
    )

    STATUS_CHOICES = (
        ('INITIATED', 'Initiated'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    transaction_id = models.CharField(max_length=100, unique=True, db_index=True)
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default='MOCK')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED')
    gateway_signature = models.CharField(max_length=255, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.order.order_number} ({self.status})"

