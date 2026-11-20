import csv
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.views.generic import View
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from apps.core.decorators import role_required
from apps.accounts.models import User
from apps.restaurants.models import Restaurant, Category, MenuItem
from apps.orders.models import Order, OrderItem, Coupon, Review
from apps.orders.services import OrderStateMachine, InvalidOrderStateTransitionError
from apps.delivery.models import DeliveryAssignment

@role_required(['admin'])
def admin_dashboard_view(request):
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)

    today_orders = Order.objects.filter(placed_at__date=today)
    today_order_count = today_orders.count()
    today_revenue = today_orders.filter(payment_status='PAID').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    active_orders_count = Order.objects.exclude(status__in=['delivered', 'cancelled', 'rejected']).count()
    active_partners_count = User.objects.filter(role='delivery_partner', is_online=True).count()

    # Chart data: last 7 days revenue & order count
    days_labels = []
    revenue_data = []
    order_data = []

    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        days_labels.append(day.strftime('%b %d'))
        day_qs = Order.objects.filter(placed_at__date=day)
        day_rev = day_qs.filter(payment_status='PAID').aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
        revenue_data.append(float(day_rev))
        order_data.append(day_qs.count())

    recent_orders = Order.objects.select_related('customer', 'restaurant', 'delivery_partner').order_by('-placed_at')[:10]
    delivery_partners = User.objects.filter(role='delivery_partner', is_active=True)

    return render(request, 'admin_panel/dashboard.html', {
        'today_order_count': today_order_count,
        'today_revenue': today_revenue,
        'active_orders_count': active_orders_count,
        'active_partners_count': active_partners_count,
        'days_labels': days_labels,
        'revenue_data': revenue_data,
        'order_data': order_data,
        'recent_orders': recent_orders,
        'delivery_partners': delivery_partners,
    })


@role_required(['admin'])
def admin_orders_list_view(request):
    orders = Order.objects.select_related('customer', 'restaurant', 'delivery_partner').order_by('-placed_at')

    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    search = request.GET.get('q', '').strip()
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(customer__email__icontains=search) |
            Q(restaurant__name__icontains=search)
        )

    delivery_partners = User.objects.filter(role='delivery_partner', is_active=True)

    return render(request, 'admin_panel/orders_list.html', {
        'orders': orders[:100],
        'status_filter': status_filter,
        'search_query': search,
        'delivery_partners': delivery_partners,
        'status_choices': Order.STATUS_CHOICES,
    })


@role_required(['admin'])
def admin_manual_assign_partner(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        partner_id = request.POST.get('partner_id')
        partner = get_object_or_404(User, id=partner_id, role='delivery_partner')

        order.delivery_partner = partner
        order.save(update_fields=['delivery_partner'])

        DeliveryAssignment.objects.update_or_create(
            order=order,
            defaults={
                'delivery_partner': partner,
                'status': 'ASSIGNED',
            }
        )

        OrderStateMachine.broadcast_order_update(order, order.status, order.status)
        messages.success(request, f"Order {order.order_number} manually assigned to {partner.get_full_name() or partner.email}")

    return redirect(request.META.get('HTTP_REFERER', '/admin-panel/orders/'))


@role_required(['admin'])
def admin_change_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        try:
            OrderStateMachine.transition_to(
                order=order,
                target_status=new_status,
                user=request.user,
                notes="Admin status override"
            )
            messages.success(request, f"Order {order.order_number} status changed to {new_status}")
        except InvalidOrderStateTransitionError as e:
            messages.error(request, str(e))

    return redirect(request.META.get('HTTP_REFERER', '/admin-panel/orders/'))


@role_required(['admin'])
def admin_users_list_view(request):
    role_filter = request.GET.get('role')
    users = User.objects.all().order_by('-created_at')
    if role_filter:
        users = users.filter(role=role_filter)

    search = request.GET.get('q', '').strip()
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone__icontains=search)
        )

    return render(request, 'admin_panel/users_list.html', {
        'users': users,
        'role_filter': role_filter,
        'search_query': search,
    })


@role_required(['admin'])
def admin_toggle_user_status(request, user_id):
    if request.method == 'POST':
        target_user = get_object_or_404(User, id=user_id)
        if target_user == request.user:
            messages.error(request, "Cannot block your own admin account.")
        else:
            target_user.is_active = not target_user.is_active
            target_user.save(update_fields=['is_active'])
            status_text = "activated" if target_user.is_active else "blocked"
            messages.success(request, f"User {target_user.email} has been {status_text}.")

    return redirect(request.META.get('HTTP_REFERER', '/admin-panel/users/'))


@role_required(['admin'])
def admin_reports_view(request):
    # Sales by day (last 30 days)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    orders = Order.objects.filter(placed_at__date__gte=thirty_days_ago, payment_status='PAID')

    # Restaurant sales
    restaurant_sales = Restaurant.objects.annotate(
        total_orders=Count('orders'),
        total_revenue=Sum('orders__total_amount')
    ).order_by('-total_revenue')

    # Top items
    top_items = OrderItem.objects.values('item_name').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('subtotal')
    ).order_by('-total_sold')[:10]

    return render(request, 'admin_panel/reports.html', {
        'restaurant_sales': restaurant_sales,
        'top_items': top_items,
    })


@role_required(['admin'])
def admin_export_csv_view(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="orders_report_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Order Number', 'Date', 'Customer Email', 'Customer Phone',
        'Restaurant', 'Status', 'Payment Method', 'Payment Status',
        'Subtotal', 'Delivery Fee', 'Tax', 'Discount', 'Total Amount',
        'Delivery Partner'
    ])

    orders = Order.objects.select_related('customer', 'restaurant', 'delivery_partner').order_by('-placed_at')
    for o in orders:
        writer.writerow([
            o.order_number,
            o.placed_at.strftime('%Y-%m-%d %H:%M:%S'),
            o.customer.email,
            o.customer.phone or '',
            o.restaurant.name,
            o.get_status_display(),
            o.payment_method,
            o.payment_status,
            o.subtotal,
            o.delivery_fee,
            o.tax_amount,
            o.discount_amount,
            o.total_amount,
            o.delivery_partner.get_full_name() if o.delivery_partner else 'Unassigned'
        ])

    return response

