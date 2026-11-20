import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from apps.orders.models import Order
from .models import Payment

class MockPaymentGatewayView(View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        if order.payment_status == 'PAID':
            return redirect('orders:live_tracking', order_id=order.id)

        return render(request, 'payments/mock_gateway.html', {
            'order': order,
            'gateway_name': 'Razorpay Test Checkout',
        })

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        action = request.POST.get('action', 'success')

        tx_id = f"pay_{uuid.uuid4().hex[:14]}"

        if action == 'success':
            payment, _ = Payment.objects.update_or_create(
                order=order,
                defaults={
                    'transaction_id': tx_id,
                    'gateway': 'MOCK',
                    'amount': order.total_amount,
                    'status': 'SUCCESS',
                    'raw_response': {'simulated': True, 'action': 'success'}
                }
            )
            order.payment_status = 'PAID'
            order.save(update_fields=['payment_status'])
            messages.success(request, f"Payment of ₹{order.total_amount} successful! Ref: {tx_id}")
            return redirect('orders:live_tracking', order_id=order.id)
        else:
            Payment.objects.update_or_create(
                order=order,
                defaults={
                    'transaction_id': tx_id,
                    'gateway': 'MOCK',
                    'amount': order.total_amount,
                    'status': 'FAILED',
                    'raw_response': {'simulated': True, 'action': 'failed'}
                }
            )
            order.payment_status = 'FAILED'
            order.save(update_fields=['payment_status'])
            messages.error(request, "Payment failed or was cancelled. Please try again.")
            return redirect('orders:checkout')

