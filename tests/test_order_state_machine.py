import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.restaurants.models import Restaurant
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.services import OrderStateMachine, InvalidOrderStateTransitionError

User = get_user_model()

@pytest.fixture
def test_setup(db):
    customer = User.objects.create_user(email='cust_test@example.com', password='password123', role='customer')
    kitchen = User.objects.create_user(email='kitch_test@example.com', password='password123', role='kitchen_staff')
    driver = User.objects.create_user(email='driver_test@example.com', password='password123', role='delivery_partner')
    admin = User.objects.create_superuser(email='admin_test@example.com', password='password123')

    restaurant = Restaurant.objects.create(
        name='Test Bistro',
        address='Connaught Place',
        phone='+9111223344',
        latitude=28.6300,
        longitude=77.2200
    )

    order = Order.objects.create(
        order_number=Order.generate_order_number(),
        customer=customer,
        restaurant=restaurant,
        status='placed',
        subtotal=Decimal('200.00'),
        delivery_fee=Decimal('30.00'),
        tax_amount=Decimal('10.00'),
        total_amount=Decimal('240.00'),
        delivery_address_text='Test Street 10',
        delivery_lat=28.6320,
        delivery_lng=77.2210
    )

    return {
        'customer': customer,
        'kitchen': kitchen,
        'driver': driver,
        'admin': admin,
        'restaurant': restaurant,
        'order': order,
    }


def test_order_valid_lifecycle_transitions(test_setup):
    order = test_setup['order']
    kitchen = test_setup['kitchen']
    driver = test_setup['driver']

    # 1. Kitchen accepts
    OrderStateMachine.transition_to(order, 'accepted', user=kitchen, prep_time_mins=25)
    order.refresh_from_db()
    assert order.status == 'accepted'
    assert order.estimated_prep_mins == 25
    assert order.accepted_at is not None

    # 2. Kitchen marks preparing
    OrderStateMachine.transition_to(order, 'preparing', user=kitchen)
    order.refresh_from_db()
    assert order.status == 'preparing'

    # 3. Kitchen marks ready
    OrderStateMachine.transition_to(order, 'ready', user=kitchen)
    order.refresh_from_db()
    assert order.status == 'ready'
    assert order.ready_at is not None

    # 4. Delivery partner picks up
    order.delivery_partner = driver
    order.save()
    OrderStateMachine.transition_to(order, 'picked_up', user=driver)
    order.refresh_from_db()
    assert order.status == 'picked_up'
    assert order.picked_up_at is not None

    # 5. Out for delivery
    OrderStateMachine.transition_to(order, 'out_for_delivery', user=driver)
    order.refresh_from_db()
    assert order.status == 'out_for_delivery'

    # 6. Delivered
    OrderStateMachine.transition_to(order, 'delivered', user=driver)
    order.refresh_from_db()
    assert order.status == 'delivered'
    assert order.delivered_at is not None
    assert order.payment_status == 'PAID'

    # Verify history logs
    histories = OrderStatusHistory.objects.filter(order=order)
    assert histories.count() >= 6


def test_invalid_order_transition_rejected(test_setup):
    order = test_setup['order']
    kitchen = test_setup['kitchen']

    # Attempt to skip directly from placed to delivered
    with pytest.raises(InvalidOrderStateTransitionError):
        OrderStateMachine.transition_to(order, 'delivered', user=kitchen)


def test_customer_cannot_cancel_after_kitchen_accepts(test_setup):
    order = test_setup['order']
    customer = test_setup['customer']
    kitchen = test_setup['kitchen']

    # Kitchen accepts the order
    OrderStateMachine.transition_to(order, 'accepted', user=kitchen)

    # Customer tries to cancel now
    with pytest.raises(InvalidOrderStateTransitionError) as excinfo:
        OrderStateMachine.transition_to(order, 'cancelled', user=customer)
    assert "cannot cancel an order once the kitchen has accepted it" in str(excinfo.value)

