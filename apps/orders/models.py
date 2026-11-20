import uuid
import random
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import BaseModel
from apps.restaurants.models import Restaurant, MenuItem

class Coupon(BaseModel):
    DISCOUNT_TYPES = (
        ('PERCENTAGE', 'Percentage'),
        ('FLAT', 'Flat Amount'),
    )
    code = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPES, default='PERCENTAGE')
    discount_value = models.DecimalField(max_digits=6, decimal_places=2) # e.g. 20 for 20% or 50 for ₹50
    min_order_value = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    max_discount_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        if subtotal < self.min_order_value:
            return Decimal('0.00')
        if self.discount_type == 'PERCENTAGE':
            discount = (subtotal * self.discount_value) / Decimal('100.00')
            if self.max_discount_amount and discount > self.max_discount_amount:
                discount = self.max_discount_amount
            return round(discount, 2)
        else: # FLAT
            return min(self.discount_value, subtotal)

    def __str__(self):
        return f"{self.code} ({self.discount_value} {self.discount_type})"


class Cart(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    applied_coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        owner = self.user.email if self.user else f"Session:{self.session_key}"
        return f"Cart of {owner} ({self.items.count()} items)"

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'menu_item')

    @property
    def unit_price(self):
        return self.menu_item.effective_price

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Order(BaseModel):
    STATUS_CHOICES = (
        ('placed', 'Order Placed'),
        ('accepted', 'Accepted by Kitchen'),
        ('preparing', 'Preparing in Kitchen'),
        ('ready', 'Food Ready for Pickup'),
        ('picked_up', 'Picked Up by Delivery Partner'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected by Kitchen'),
    )

    PAYMENT_METHODS = (
        ('COD', 'Cash on Delivery'),
        ('ONLINE', 'Online Payment (Razorpay/Card)'),
    )

    PAYMENT_STATUS = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    )

    ORDER_TYPES = (
        ('DELIVERY', 'Delivery'),
        ('DINE_IN', 'Dine-In (Table Order)'),
        ('TAKEAWAY', 'Takeaway'),
    )

    order_number = models.CharField(max_length=30, unique=True, db_index=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    delivery_partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')

    order_type = models.CharField(max_length=20, choices=ORDER_TYPES, default='DELIVERY', db_index=True)
    table_number = models.CharField(max_length=20, blank=True, null=True, db_index=True)

    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='placed', db_index=True)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS, default='COD')
    payment_status = models.CharField(max_length=15, choices=PAYMENT_STATUS, default='PENDING')

    # Price breakdowns
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('30.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00')) # 5% GST
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = models.CharField(max_length=20, blank=True)

    # Address snapshot & coords
    delivery_address_title = models.CharField(max_length=50, default='Home', blank=True)
    delivery_address_text = models.TextField(blank=True, default='')
    delivery_lat = models.FloatField(default=28.6139)
    delivery_lng = models.FloatField(default=77.2090)
    special_instructions = models.TextField(blank=True)

    # Security OTPs for Delivery Chain
    pickup_otp = models.CharField(max_length=6, default='1234')
    delivery_otp = models.CharField(max_length=6, default='5678')

    # Timing & ETAs
    estimated_prep_mins = models.PositiveIntegerField(default=20)
    placed_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-placed_at']

    def __str__(self):
        return f"{self.order_number} - {self.customer.email} (₹{self.total_amount})"

    @classmethod
    def generate_order_number(cls):
        while True:
            rand_suffix = random.randint(100000, 999999)
            num = f"QB-{rand_suffix}"
            if not cls.objects.filter(order_number=num).exists():
                return num


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True)
    item_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.item_name} @ ₹{self.price}"


class OrderStatusHistory(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    changed_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    changed_by_role = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.order.order_number}: {self.from_status} -> {self.to_status} ({self.created_at:%H:%M:%S})"


class Review(BaseModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(default=5) # 1 to 5
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.restaurant.name} by {self.customer.email} ({self.rating}★)"

