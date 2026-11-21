from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.core.decorators import role_required
from apps.core.utils import haversine_distance
from apps.orders.models import Order
from apps.orders.services import OrderStateMachine, InvalidOrderStateTransitionError
from .models import DeliveryAssignment, DeliveryLocationLog

@role_required(['delivery_partner', 'admin'])
def delivery_dashboard_view(request):
    user = request.user
    
    # Active assignment check
    active_assignment = DeliveryAssignment.objects.filter(
        delivery_partner=user,
        status__in=['ASSIGNED', 'PICKED_UP']
    ).select_related('order', 'order__restaurant', 'order__customer').first()

    # Calculate earnings
    today = timezone.now().date()
    today_earnings = DeliveryAssignment.objects.filter(
        delivery_partner=user,
        status='DELIVERED',
        delivered_at__date=today
    ).aggregate(total=Sum('partner_earnings'))['total'] or Decimal('0.00')

    week_ago = timezone.now() - timezone.timedelta(days=7)
    week_earnings = DeliveryAssignment.objects.filter(
        delivery_partner=user,
        status='DELIVERED',
        delivered_at__gte=week_ago
    ).aggregate(total=Sum('partner_earnings'))['total'] or Decimal('0.00')

    delivered_count = DeliveryAssignment.objects.filter(
        delivery_partner=user,
        status='DELIVERED',
        delivered_at__date=today
    ).count()

    return render(request, 'delivery/dashboard.html', {
        'partner': user,
        'active_assignment': active_assignment,
        'today_earnings': today_earnings,
        'week_earnings': week_earnings,
        'delivered_count': delivered_count,
    })


class ToggleOnlineStatusAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        user.is_online = not user.is_online
        user.save(update_fields=['is_online'])
        return Response({'success': True, 'is_online': user.is_online})


class UpdateLocationAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            lat = float(request.data.get('latitude'))
            lng = float(request.data.get('longitude'))
        except (TypeError, ValueError):
            return Response({'error': 'Invalid latitude/longitude'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        user.current_lat = lat
        user.current_lng = lng
        user.last_location_updated_at = now
        user.save(update_fields=['current_lat', 'current_lng', 'last_location_updated_at'])

        # Check for active delivery order
        active_assignment = DeliveryAssignment.objects.filter(
            delivery_partner=user,
            status__in=['ASSIGNED', 'PICKED_UP']
        ).select_related('order').first()

        if active_assignment:
            order = active_assignment.order
            DeliveryLocationLog.objects.create(
                delivery_partner=user,
                order=order,
                latitude=lat,
                longitude=lng
            )

            # Broadcast real-time driver coordinates to customer tracking page
            channel_layer = get_channel_layer()
            if channel_layer:
                try:
                    async_to_sync(channel_layer.group_send)(
                        f"order_{order.id}",
                        {
                            'type': 'driver_location_update',
                            'order_id': str(order.id),
                            'partner_lat': lat,
                            'partner_lng': lng,
                            'timestamp': now.isoformat(),
                        }
                    )
                except Exception:
                    pass

        return Response({'success': True, 'lat': lat, 'lng': lng})


class AvailableOrdersAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if getattr(user, 'role', None) not in ['delivery_partner', 'admin'] and not user.is_superuser:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        p_lat = user.current_lat or 28.6139
        p_lng = user.current_lng or 77.2090

        # Orders that are preparing or ready and not yet assigned
        orders = Order.objects.filter(
            status__in=['preparing', 'ready'],
            delivery_partner__isnull=True
        ).select_related('restaurant')

        nearby_list = []
        for o in orders:
            dist = haversine_distance(p_lat, p_lng, o.restaurant.latitude, o.restaurant.longitude)
            # Estimate driver earning: ₹40 base + ₹12/km
            earning = Decimal('40.00') + Decimal(f"{dist * 12.0:.2f}")
            nearby_list.append({
                'order_id': str(o.id),
                'order_number': o.order_number,
                'status': o.status,
                'status_display': o.get_status_display(),
                'restaurant_name': o.restaurant.name,
                'restaurant_address': o.restaurant.address,
                'delivery_address': o.delivery_address_text,
                'distance_km': dist,
                'earning': round(earning, 2),
                'total_amount': o.total_amount,
                'items_count': o.items.count(),
            })

        # Sort by distance
        nearby_list.sort(key=lambda x: x['distance_km'])

        return Response({'orders': nearby_list})


class AcceptOrderAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        user = request.user
        if user.role not in ['delivery_partner', 'admin'] and not user.is_superuser:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            # Concurrency protection: select_for_update prevents race conditions!
            try:
                order = Order.objects.select_for_update().get(id=order_id)
            except Order.DoesNotExist:
                return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

            if order.delivery_partner is not None:
                return Response({
                    'error': 'This order was already accepted by another delivery partner!'
                }, status=status.HTTP_409_CONFLICT)

            if order.status in ['delivered', 'cancelled', 'rejected']:
                return Response({
                    'error': f'Order cannot be accepted because it is already {order.status}.'
                }, status=status.HTTP_400_BAD_REQUEST)

            order.delivery_partner = user
            order.save(update_fields=['delivery_partner'])

            p_lat = user.current_lat or 28.6139
            p_lng = user.current_lng or 77.2090
            dist = haversine_distance(p_lat, p_lng, order.restaurant.latitude, order.restaurant.longitude)
            earnings = Decimal('40.00') + Decimal(f"{dist * 12.0:.2f}")

            assignment = DeliveryAssignment.objects.create(
                order=order,
                delivery_partner=user,
                status='ASSIGNED',
                partner_earnings=earnings,
                distance_km=dist
            )

        # Notify via channels
        OrderStateMachine.broadcast_order_update(order, order.status, order.status)

        return Response({
            'success': True,
            'message': 'Order accepted successfully!',
            'order_id': str(order.id),
            'order_number': order.order_number,
        })


class VerifyPickupOTPAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        otp = request.data.get('otp', '').strip()
        assignment = get_object_or_404(
            DeliveryAssignment.objects.select_related('order'),
            order_id=order_id,
            delivery_partner=request.user
        )
        order = assignment.order

        if order.pickup_otp != otp:
            return Response({'error': 'Invalid Pickup OTP code. Ask restaurant kitchen staff for the code.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            OrderStateMachine.transition_to(
                order=order,
                target_status='picked_up',
                user=request.user,
                notes="Pickup verified by delivery partner via OTP."
            )
            assignment.status = 'PICKED_UP'
            assignment.save(update_fields=['status'])
            return Response({'success': True, 'message': 'Pickup verified! Proceed to customer location.'})
        except InvalidOrderStateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyDeliveryOTPAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        otp = request.data.get('otp', '').strip()
        assignment = get_object_or_404(
            DeliveryAssignment.objects.select_related('order'),
            order_id=order_id,
            delivery_partner=request.user
        )
        order = assignment.order

        if order.delivery_otp != otp:
            return Response({'error': 'Invalid Delivery OTP. Ask the customer for their delivery verification code.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            OrderStateMachine.transition_to(
                order=order,
                target_status='delivered',
                user=request.user,
                notes="Delivery verified by customer via OTP."
            )
            assignment.status = 'DELIVERED'
            assignment.delivered_at = timezone.now()
            assignment.save(update_fields=['status', 'delivered_at'])
            return Response({'success': True, 'message': 'Order marked as Delivered! Earnings credited.'})
        except InvalidOrderStateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
