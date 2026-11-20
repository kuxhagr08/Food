import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.restaurants.models import Restaurant
from apps.orders.models import Order
from apps.delivery.models import DeliveryAssignment

User = get_user_model()

@pytest.fixture
def concurrency_setup(db):
    partner1 = User.objects.create_user(email='driver1@quickbite.com', password='pass', role='delivery_partner')
    partner2 = User.objects.create_user(email='driver2@quickbite.com', password='pass', role='delivery_partner')
    cust = User.objects.create_user(email='cust_conc@quickbite.com', password='pass', role='customer')

    rest = Restaurant.objects.create(name='Express Diner', address='Main road', phone='1234')
    order = Order.objects.create(
        order_number=Order.generate_order_number(),
        customer=cust,
        restaurant=rest,
        status='ready',
        subtotal=Decimal('300.00'),
        delivery_fee=Decimal('30.00'),
        total_amount=Decimal('330.00'),
        delivery_address_text='Sector 4',
        delivery_lat=28.6139,
        delivery_lng=77.2090
    )
    return {
        'partner1': partner1,
        'partner2': partner2,
        'order': order,
    }


def test_two_partners_accepting_same_order_race_condition(concurrency_setup):
    order = concurrency_setup['order']
    p1 = concurrency_setup['partner1']
    p2 = concurrency_setup['partner2']

    client1 = APIClient()
    client1.force_authenticate(user=p1)

    client2 = APIClient()
    client2.force_authenticate(user=p2)

    # 1. Partner 1 accepts order
    res1 = client1.post(f'/delivery/api/orders/{order.id}/accept/')
    assert res1.status_code == 200
    assert res1.data['success'] is True

    # Order should now belong to Partner 1
    order.refresh_from_db()
    assert order.delivery_partner == p1
    assert DeliveryAssignment.objects.filter(order=order, delivery_partner=p1).exists()

    # 2. Partner 2 tries to accept the exact same order
    res2 = client2.post(f'/delivery/api/orders/{order.id}/accept/')
    # Must fail with 409 Conflict due to select_for_update atomic locking
    assert res2.status_code == 409
    assert 'already accepted' in res2.data['error']

    # Partner 2 must NOT overwrite the assignment
    order.refresh_from_db()
    assert order.delivery_partner == p1

