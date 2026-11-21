import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import View, TemplateView
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from apps.core.utils import generate_otp
from apps.restaurants.models import Restaurant, MenuItem
from apps.accounts.models import Address
from .models import Cart, CartItem, Order, OrderItem, Coupon, Review
from .services import PriceCalculator, OrderStateMachine, InvalidOrderStateTransitionError

def get_or_create_user_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
        return cart


class CartView(View):
    def get(self, request):
        cart = get_or_create_user_cart(request)
        cart_items = cart.items.select_related('menu_item', 'menu_item__restaurant').all()
        
        restaurant = cart.restaurant
        items_data = [{'menu_item': ci.menu_item, 'quantity': ci.quantity} for ci in cart_items]
        
        calc = PriceCalculator.calculate(
            items_data=items_data,
            restaurant=restaurant if restaurant else (cart_items[0].menu_item.restaurant if cart_items else None),
            coupon_code=cart.applied_coupon.code if cart.applied_coupon else None
        )

        return render(request, 'customer/cart.html', {
            'cart': cart,
            'cart_items': cart_items,
            'pricing': calc,
            'restaurant': restaurant,
        })


class AddToCartAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        item_id = request.data.get('item_id')
        qty = int(request.data.get('quantity', 1))
        clear_existing = request.data.get('clear_existing', False)

        item = get_object_or_404(MenuItem, id=item_id)
        if not item.is_available:
            return Response({'error': f"'{item.name}' is currently sold out."}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_user_cart(request)

        # Multi-restaurant check
        if cart.restaurant and cart.restaurant != item.restaurant:
            if not clear_existing:
                return Response({
                    'conflict': True,
                    'current_restaurant': cart.restaurant.name,
                    'new_restaurant': item.restaurant.name,
                    'message': f"Your cart contains items from {cart.restaurant.name}. Would you like to discard and start a new order with {item.restaurant.name}?"
                }, status=status.HTTP_409_CONFLICT)
            else:
                cart.items.all().delete()
                cart.applied_coupon = None

        cart.restaurant = item.restaurant
        cart.save(update_fields=['restaurant'])

        cart_item, created = CartItem.objects.get_or_create(cart=cart, menu_item=item)
        if not created:
            cart_item.quantity += qty
        else:
            cart_item.quantity = qty

        if cart_item.quantity <= 0:
            cart_item.delete()
        else:
            cart_item.save()

        # Check if cart is now empty
        if not cart.items.exists():
            cart.restaurant = None
            cart.applied_coupon = None
            cart.save()

        total_count = cart.items.count()
        return Response({
            'success': True,
            'cart_count': total_count,
            'item_id': str(item.id),
            'item_name': item.name,
            'quantity': cart_item.quantity if cart_item.pk else 0,
        })


class UpdateCartItemAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        item_id = request.data.get('item_id')
        action = request.data.get('action') # 'increase', 'decrease', 'remove'

        cart = get_or_create_user_cart(request)
        cart_item = get_object_or_404(CartItem, cart=cart, menu_item_id=item_id)

        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
        elif action == 'decrease':
            cart_item.quantity -= 1
            if cart_item.quantity <= 0:
                cart_item.delete()
            else:
                cart_item.save()
        elif action == 'remove':
            cart_item.delete()

        if not cart.items.exists():
            cart.restaurant = None
            cart.applied_coupon = None
            cart.save()

        return Response({
            'success': True,
            'cart_count': cart.items.count(),
        })


class ApplyCouponAPI(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        code = request.data.get('code', '').strip()
        cart = get_or_create_user_cart(request)

        if not code:
            cart.applied_coupon = None
            cart.save(update_fields=['applied_coupon'])
            return Response({'success': True, 'message': 'Coupon removed'})

        try:
            coupon = Coupon.objects.get(code__iexact=code)
            if not coupon.is_valid_now():
                return Response({'error': 'Coupon is expired or inactive.'}, status=status.HTTP_400_BAD_REQUEST)
            if cart.subtotal < coupon.min_order_value:
                return Response({'error': f'Minimum order value for this coupon is ₹{coupon.min_order_value}'}, status=status.HTTP_400_BAD_REQUEST)

            cart.applied_coupon = coupon
            cart.save(update_fields=['applied_coupon'])
            discount = coupon.calculate_discount(cart.subtotal)
            return Response({'success': True, 'discount': discount, 'message': f"Coupon '{coupon.code}' applied!"})
        except Coupon.DoesNotExist:
            return Response({'error': 'Invalid coupon code.'}, status=status.HTTP_404_NOT_FOUND)


class CheckoutView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect(f'/accounts/login/?next={request.get_full_path()}')

        cart = get_or_create_user_cart(request)
        cart_items = cart.items.select_related('menu_item').all()
        if not cart_items or not cart.restaurant:
            messages.info(request, "Your cart is empty.")
            return redirect('restaurants:list')

        # Check Dine-In Table param
        table_number = request.GET.get('table') or request.session.get('dine_in_table')
        is_dine_in = bool(table_number)

        addresses = request.user.addresses.all().order_by('-is_default')
        default_address = addresses.filter(is_default=True).first() or addresses.first()

        items_data = [{'menu_item': ci.menu_item, 'quantity': ci.quantity} for ci in cart_items]
        calc = PriceCalculator.calculate(
            items_data=items_data,
            restaurant=cart.restaurant,
            delivery_lat=default_address.latitude if default_address else 28.6139,
            delivery_lng=default_address.longitude if default_address else 77.2090,
            coupon_code=cart.applied_coupon.code if cart.applied_coupon else None,
            is_dine_in=is_dine_in
        )

        return render(request, 'customer/checkout.html', {
            'cart': cart,
            'cart_items': cart_items,
            'addresses': addresses,
            'default_address': default_address,
            'pricing': calc,
            'restaurant': cart.restaurant,
            'is_dine_in': is_dine_in,
            'table_number': table_number,
        })


class PlaceOrderAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart = get_or_create_user_cart(request)
        cart_items = cart.items.select_related('menu_item', 'menu_item__restaurant').all()

        if not cart_items or not cart.restaurant:
            return Response({'error': 'Your cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        order_type = request.data.get('order_type', 'DELIVERY') # 'DELIVERY' or 'DINE_IN'
        table_number = request.data.get('table_number', '').strip()
        is_dine_in = (order_type == 'DINE_IN')

        address_id = request.data.get('address_id')
        raw_payment_method = request.data.get('payment_method', 'COD').upper()
        # Normalize payment method into Model's supported choices ('COD' or 'ONLINE')
        is_online = raw_payment_method in ['ONLINE', 'UPI', 'CARD', 'NETBANKING']
        payment_method = 'ONLINE' if is_online else 'COD'
        special_instructions = request.data.get('special_instructions', '').strip()

        if is_dine_in:
            if not table_number:
                return Response({'error': 'Table number is required for Dine-in orders.'}, status=status.HTTP_400_BAD_REQUEST)
            address_title = f"Table #{table_number}"
            address_text = f"Dine-In Table #{table_number} at {cart.restaurant.name}"
            del_lat = cart.restaurant.latitude
            del_lng = cart.restaurant.longitude
        else:
            address = None
            if address_id:
                address = Address.objects.filter(id=address_id, user=request.user).first()
            if not address:
                address = request.user.addresses.filter(is_default=True).first() or request.user.addresses.first()

            if address:
                address_title = address.title
                address_text = f"{address.address_line1}, {address.address_line2 or ''}, {address.city} - {address.pincode}".replace(' ,', '')
                del_lat = address.latitude or 28.570
                del_lng = address.longitude or 77.320
            else:
                # Seamless checkout: auto-create address from request payload or user location
                line1 = (request.data.get('address_line1') or 'Address').strip()
                city = (request.data.get('city') or 'Noida').strip()
                pincode = (request.data.get('pincode') or '201301').strip()
                try:
                    del_lat = float(request.data.get('latitude', 28.570))
                    del_lng = float(request.data.get('longitude', 77.320))
                except (ValueError, TypeError):
                    del_lat, del_lng = 28.570, 77.320

                new_addr = Address.objects.create(
                    user=request.user,
                    title='Home',
                    address_line1=line1,
                    city=city,
                    pincode=pincode,
                    latitude=del_lat,
                    longitude=del_lng,
                    is_default=True
                )
                address_title = new_addr.title
                address_text = f"{new_addr.address_line1}, {new_addr.city} - {new_addr.pincode}"

        # Server-side price calculation
        items_data = [{'menu_item': ci.menu_item, 'quantity': ci.quantity} for ci in cart_items]
        calc = PriceCalculator.calculate(
            items_data=items_data,
            restaurant=cart.restaurant,
            delivery_lat=del_lat,
            delivery_lng=del_lng,
            coupon_code=cart.applied_coupon.code if cart.applied_coupon else None,
            is_dine_in=is_dine_in
        )

        with transaction.atomic():
            order = Order.objects.create(
                order_number=Order.generate_order_number(),
                customer=request.user,
                restaurant=cart.restaurant,
                order_type=order_type,
                table_number=table_number if is_dine_in else '',
                payment_method=payment_method,
                payment_status='PAID' if payment_method == 'ONLINE' else 'PENDING',
                subtotal=calc['subtotal'],
                delivery_fee=calc['delivery_fee'],
                tax_amount=calc['tax_amount'],
                discount_amount=calc['discount_amount'],
                total_amount=calc['total_amount'],
                coupon_code=cart.applied_coupon.code if cart.applied_coupon else '',
                delivery_address_title=address_title,
                delivery_address_text=address_text,
                delivery_lat=del_lat,
                delivery_lng=del_lng,
                special_instructions=special_instructions,
                pickup_otp=generate_otp(4),
                delivery_otp=generate_otp(4),
                estimated_prep_mins=cart.restaurant.avg_prep_time_mins,
            )

            # Create order items snapshot
            for ci in cart_items:
                OrderItem.objects.create(
                    order=order,
                    menu_item=ci.menu_item,
                    item_name=ci.menu_item.name,
                    price=ci.menu_item.effective_price,
                    quantity=ci.quantity,
                    subtotal=ci.subtotal
                )

            # Increment coupon usage
            if cart.applied_coupon:
                cart.applied_coupon.used_count += 1
                cart.applied_coupon.save(update_fields=['used_count'])

            # Clear cart
            cart.items.all().delete()
            cart.restaurant = None
            cart.applied_coupon = None
            cart.save()

            # Record initial history
            OrderStateMachine.broadcast_order_update(order, 'created', 'placed')

        method_param = raw_payment_method.lower() if is_online else 'cod'
        redirect_url = f"/payments/mock-gateway/{order.id}/?method={method_param}" if is_online else f"/orders/{order.id}/tracking/"

        return Response({
            'success': True,
            'order_id': str(order.id),
            'order_number': order.order_number,
            'total_amount': order.total_amount,
            'is_online': is_online,
            'redirect_url': redirect_url
        })


class LiveOrderTrackingView(View):
    def get(self, request, order_id):
        if not request.user.is_authenticated:
            return redirect(f'/accounts/login/?next={request.get_full_path()}')

        # Allow customer who owns the order, or staff/admin
        order = get_object_or_404(Order.objects.select_related('restaurant', 'delivery_partner', 'customer'), id=order_id)
        if request.user != order.customer and getattr(request.user, 'role', None) not in ['admin', 'kitchen_staff', 'delivery_partner'] and not request.user.is_superuser:
            messages.error(request, "Unauthorized access to order tracking.")
            return redirect('/')

        status_steps = [
            {'key': 'placed', 'label': 'Order Placed'},
            {'key': 'accepted', 'label': 'Accepted'},
            {'key': 'preparing', 'label': 'Preparing Food'},
            {'key': 'ready', 'label': 'Ready for Pickup'},
            {'key': 'picked_up', 'label': 'Picked Up'},
            {'key': 'out_for_delivery', 'label': 'Out for Delivery'},
            {'key': 'delivered', 'label': 'Delivered'},
        ]

        # Calculate progress index
        status_keys = [s['key'] for s in status_steps]
        current_step_idx = 0
        if order.status in status_keys:
            current_step_idx = status_keys.index(order.status)
        elif order.status in ['cancelled', 'rejected']:
            current_step_idx = -1

        return render(request, 'customer/live_tracking.html', {
            'order': order,
            'status_steps': status_steps,
            'current_step_idx': current_step_idx,
            'order_items': order.items.all(),
        })


class OrderHistoryView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        orders = Order.objects.filter(customer=request.user).select_related('restaurant').prefetch_related('items').order_by('-placed_at')
        return render(request, 'customer/order_history.html', {'orders': orders})


class CancelOrderAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, customer=request.user)
        reason = request.data.get('reason', 'Customer requested cancellation')
        try:
            OrderStateMachine.transition_to(
                order=order,
                target_status='cancelled',
                user=request.user,
                reason=reason
            )
            return Response({'success': True, 'message': 'Order has been cancelled.'})
        except InvalidOrderStateTransitionError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewSubmitAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, customer=request.user, status='delivered')
        if hasattr(order, 'review'):
            return Response({'error': 'You have already reviewed this order.'}, status=status.HTTP_400_BAD_REQUEST)

        rating = int(request.data.get('rating', 5))
        comment = request.data.get('comment', '').strip()

        Review.objects.create(
            order=order,
            customer=request.user,
            restaurant=order.restaurant,
            rating=rating,
            comment=comment
        )

        # Recalculate restaurant rating
        reviews = Review.objects.filter(restaurant=order.restaurant)
        avg = sum(r.rating for r in reviews) / reviews.count()
        order.restaurant.rating = round(avg, 1)
        order.restaurant.total_ratings = reviews.count()
        order.restaurant.save(update_fields=['rating', 'total_ratings'])

        return Response({'success': True, 'message': 'Thank you for your rating!'})

