from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from apps.core.decorators import role_required
from apps.restaurants.models import Restaurant, MenuItem
from apps.orders.models import Order
from apps.orders.services import OrderStateMachine, InvalidOrderStateTransitionError

@role_required(['kitchen_staff', 'admin'])
def kitchen_dashboard_view(request):
    # Admin can select restaurant or view default; kitchen staff views their assigned restaurant
    selected_restaurant_id = request.GET.get('restaurant_id')
    all_restaurants = Restaurant.objects.filter(is_active=True)

    if selected_restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=selected_restaurant_id)
    else:
        # If user owns or is attached to a restaurant
        restaurant = Restaurant.objects.filter(is_active=True).first()

    return render(request, 'kitchen/dashboard.html', {
        'restaurant': restaurant,
        'all_restaurants': all_restaurants,
    })


class KitchenOrdersDataAPI(APIView):
    """Returns JSON payload of New, Preparing, and Ready orders for KDS screen."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['kitchen_staff', 'admin'] and not request.user.is_superuser:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        restaurant_id = request.GET.get('restaurant_id')
        if restaurant_id:
            restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        else:
            restaurant = Restaurant.objects.filter(is_active=True).first()

        if not restaurant:
            return Response({'error': 'No active restaurant found'}, status=status.HTTP_404_NOT_FOUND)

        orders_qs = Order.objects.filter(
            restaurant=restaurant,
            status__in=['placed', 'accepted', 'preparing', 'ready']
        ).prefetch_related('items').order_by('placed_at')

        def serialize_order(o):
            now = timezone.now()
            mins_elapsed = int((now - o.placed_at).total_seconds() // 60)
            return {
                'id': str(o.id),
                'order_number': o.order_number,
                'status': o.status,
                'status_display': o.get_status_display(),
                'placed_at': o.placed_at.strftime('%H:%M'),
                'mins_elapsed': mins_elapsed,
                'is_delayed': mins_elapsed > 20,
                'total_amount': str(o.total_amount),
                'order_type': o.order_type,
                'table_number': o.table_number or '',
                'special_instructions': o.special_instructions,
                'pickup_otp': o.pickup_otp,
                'estimated_prep_mins': o.estimated_prep_mins,
                'items': [
                    {
                        'name': item.item_name,
                        'quantity': item.quantity,
                        'price': str(item.price),
                    }
                    for item in o.items.all()
                ]
            }

        new_orders = [serialize_order(o) for o in orders_qs if o.status == 'placed']
        preparing_orders = [serialize_order(o) for o in orders_qs if o.status in ['accepted', 'preparing']]
        ready_orders = [serialize_order(o) for o in orders_qs if o.status == 'ready']

        # Get menu items for quick stock toggle
        menu_items = [
            {
                'id': str(i.id),
                'name': i.name,
                'price': str(i.price),
                'is_available': i.is_available,
                'is_veg': i.is_veg,
            }
            for i in restaurant.menu_items.all()
        ]

        return Response({
            'restaurant_id': str(restaurant.id),
            'restaurant_name': restaurant.name,
            'new_orders': new_orders,
            'preparing_orders': preparing_orders,
            'ready_orders': ready_orders,
            'menu_items': menu_items,
        })


class AcceptKitchenOrderAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        if getattr(request.user, 'role', None) not in ['kitchen_staff', 'admin'] and not request.user.is_superuser:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        order = get_object_or_404(Order, id=order_id)
        prep_time = int(request.data.get('prep_time', 20))

        try:
            OrderStateMachine.transition_to(
                order=order,
                target_status='accepted',
                user=request.user,
                prep_time_mins=prep_time,
                notes=f"Accepted by kitchen with {prep_time} min prep time."
            )
            return Response({'success': True, 'message': f'Order accepted. ETA {prep_time} mins.'})
        except InvalidOrderStateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RejectKitchenOrderAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        if getattr(request.user, 'role', None) not in ['kitchen_staff', 'admin'] and not request.user.is_superuser:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        order = get_object_or_404(Order, id=order_id)
        reason = request.data.get('reason', 'Kitchen busy or item unavailable').strip()

        try:
            OrderStateMachine.transition_to(
                order=order,
                target_status='rejected',
                user=request.user,
                reason=reason,
                notes=f"Rejected: {reason}"
            )
            return Response({'success': True, 'message': 'Order rejected.'})
        except InvalidOrderStateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MarkPreparingAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        if getattr(request.user, 'role', None) not in ['kitchen_staff', 'admin'] and not request.user.is_superuser:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        order = get_object_or_404(Order, id=order_id)
        try:
            OrderStateMachine.transition_to(
                order=order,
                target_status='preparing',
                user=request.user,
                notes="Food is now being prepared in kitchen."
            )
            return Response({'success': True, 'message': 'Status updated to Preparing.'})
        except InvalidOrderStateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MarkReadyAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        if getattr(request.user, 'role', None) not in ['kitchen_staff', 'admin'] and not request.user.is_superuser:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        order = get_object_or_404(Order, id=order_id)
        try:
            OrderStateMachine.transition_to(
                order=order,
                target_status='ready',
                user=request.user,
                notes="Food prepared and packaged. Ready for pickup."
            )
            return Response({'success': True, 'message': 'Order marked Ready! Drivers notified.'})
        except InvalidOrderStateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

