from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.core.utils import haversine_distance, calculate_delivery_fee
from apps.restaurants.models import Restaurant, MenuItem
from .models import Order, OrderStatusHistory, Coupon

class InvalidOrderStateTransitionError(Exception):
    """Raised when an order status change is not allowed."""
    pass


class OrderStateMachine:
    VALID_TRANSITIONS = {
        'placed': ['accepted', 'rejected', 'cancelled'],
        'accepted': ['preparing', 'cancelled'],
        'preparing': ['ready', 'cancelled'],
        'ready': ['picked_up', 'cancelled'],
        'picked_up': ['out_for_delivery', 'delivered'],
        'out_for_delivery': ['delivered'],
        'delivered': [],
        'cancelled': [],
        'rejected': [],
    }

    ROLE_PERMISSIONS = {
        'accepted': ['kitchen_staff', 'admin'],
        'rejected': ['kitchen_staff', 'admin'],
        'preparing': ['kitchen_staff', 'admin'],
        'ready': ['kitchen_staff', 'admin'],
        'picked_up': ['delivery_partner', 'admin'],
        'out_for_delivery': ['delivery_partner', 'admin'],
        'delivered': ['delivery_partner', 'admin'],
        'cancelled': ['customer', 'admin', 'kitchen_staff'],
    }

    @classmethod
    def can_transition(cls, current_status: str, target_status: str) -> bool:
        allowed = cls.VALID_TRANSITIONS.get(current_status, [])
        return target_status in allowed

    @classmethod
    def transition_to(
        cls,
        order: Order,
        target_status: str,
        user=None,
        role=None,
        notes: str = "",
        prep_time_mins: int = None,
        reason: str = ""
    ) -> Order:
        """
        Executes an atomic status transition for an order.
        Validates transition matrix and role permissions, logs history,
        and broadcasts updates to relevant WebSocket groups.
        """
        current_status = order.status
        user_role = role or (user.role if user and hasattr(user, 'role') else 'system')
        if user and user.is_superuser:
            user_role = 'admin'

        if not cls.can_transition(current_status, target_status):
            raise InvalidOrderStateTransitionError(
                f"Cannot change order status from '{current_status}' to '{target_status}'."
            )

        allowed_roles = cls.ROLE_PERMISSIONS.get(target_status, [])
        if allowed_roles and user_role not in allowed_roles:
            raise InvalidOrderStateTransitionError(
                f"Role '{user_role}' is not authorized to transition order to '{target_status}'."
            )

        # Customer cancellation rule: only if still in 'placed' status
        if user_role == 'customer' and target_status == 'cancelled' and current_status != 'placed':
            raise InvalidOrderStateTransitionError(
                "You cannot cancel an order once the kitchen has accepted it."
            )

        with transaction.atomic():
            now = timezone.now()
            order.status = target_status

            if target_status == 'accepted':
                order.accepted_at = now
                if prep_time_mins:
                    order.estimated_prep_mins = prep_time_mins
            elif target_status == 'ready':
                order.ready_at = now
            elif target_status == 'picked_up':
                order.picked_up_at = now
            elif target_status == 'delivered':
                order.delivered_at = now
                order.payment_status = 'PAID' # Completed delivery implies payment cleared
            elif target_status in ['cancelled', 'rejected']:
                order.cancelled_at = now
                if reason:
                    order.cancellation_reason = reason

            order.save()

            # Record in status history
            history_note = notes or reason or f"Status changed to {target_status}"
            OrderStatusHistory.objects.create(
                order=order,
                from_status=current_status,
                to_status=target_status,
                changed_by_user=user if user and user.is_authenticated else None,
                changed_by_role=user_role,
                notes=history_note
            )

        # Broadcast via Channels
        cls.broadcast_order_update(order, current_status, target_status)

        return order

    @classmethod
    def broadcast_order_update(cls, order: Order, from_status: str, to_status: str):
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        payload = {
            'type': 'order_status_update',
            'order_id': str(order.id),
            'order_number': order.order_number,
            'from_status': from_status,
            'to_status': to_status,
            'status_display': order.get_status_display(),
            'timestamp': timezone.now().isoformat(),
            'estimated_prep_mins': order.estimated_prep_mins,
            'order_type': order.order_type,
            'table_number': order.table_number,
            'partner_name': order.delivery_partner.get_full_name() if order.delivery_partner else None,
            'partner_phone': order.delivery_partner.phone if order.delivery_partner else None,
        }

        try:
            # 1. Customer live tracking group
            async_to_sync(channel_layer.group_send)(f"order_{order.id}", payload)
            # 2. Kitchen group
            async_to_sync(channel_layer.group_send)(f"kitchen_{order.restaurant.id}", payload)
            # 3. Delivery partner group (especially useful when status is 'ready' for nearby broadcast)
            async_to_sync(channel_layer.group_send)("delivery_partners", payload)
            # 4. Admin group
            async_to_sync(channel_layer.group_send)("admin", payload)
        except Exception as e:
            # Avoid breaking business logic if channel layer has connection issue
            pass


class PriceCalculator:
    """Calculates order totals server-side with strict precision."""
    TAX_RATE = Decimal('0.05') # 5% GST

    @classmethod
    def calculate(
        cls,
        items_data: list,
        restaurant: Restaurant,
        delivery_lat: float = None,
        delivery_lng: float = None,
        coupon_code: str = None,
        is_dine_in: bool = False
    ) -> dict:
        """
        items_data format: [{'menu_item': MenuItem instance, 'quantity': int}, ...]
        Returns breakdown dict:
        {
            'subtotal': Decimal,
            'tax_amount': Decimal,
            'delivery_fee': Decimal,
            'discount_amount': Decimal,
            'total_amount': Decimal,
            'coupon': Coupon or None,
            'distance_km': float
        }
        """
        subtotal = Decimal('0.00')
        for item_entry in items_data:
            item = item_entry['menu_item']
            qty = item_entry['quantity']
            unit_price = item.effective_price
            subtotal += unit_price * qty

        tax_amount = round(subtotal * cls.TAX_RATE, 2)

        # Distance & Delivery fee
        distance_km = 0.0
        if delivery_lat and delivery_lng and restaurant.latitude and restaurant.longitude:
            distance_km = haversine_distance(
                restaurant.latitude, restaurant.longitude,
                delivery_lat, delivery_lng
            )
        delivery_fee = calculate_delivery_fee(distance_km)
        if is_dine_in:
            delivery_fee = Decimal('0.00')

        # Coupon Discount
        discount_amount = Decimal('0.00')
        applied_coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code.strip())
                if coupon.is_valid_now() and subtotal >= coupon.min_order_value:
                    discount_amount = coupon.calculate_discount(subtotal)
                    applied_coupon = coupon
            except Coupon.DoesNotExist:
                pass

        total_amount = max(Decimal('0.00'), (subtotal + tax_amount + delivery_fee) - discount_amount)

        return {
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'delivery_fee': delivery_fee,
            'discount_amount': discount_amount,
            'total_amount': total_amount,
            'coupon': applied_coupon,
            'distance_km': distance_km,
        }

