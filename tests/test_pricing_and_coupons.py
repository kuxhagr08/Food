import pytest
from decimal import Decimal
from apps.core.utils import haversine_distance, calculate_delivery_fee
from apps.restaurants.models import Restaurant, MenuItem, Category
from apps.orders.models import Coupon
from apps.orders.services import PriceCalculator

@pytest.fixture
def pricing_setup(db):
    rest = Restaurant.objects.create(
        name='Pizza Hub',
        address='Central Market',
        phone='1234567890',
        latitude=28.6139,
        longitude=77.2090
    )
    cat = Category.objects.create(name='Pizzas', icon='🍕')
    item1 = MenuItem.objects.create(
        restaurant=rest,
        category=cat,
        name='Margherita',
        price=Decimal('200.00'),
        discount_price=Decimal('180.00')
    )
    item2 = MenuItem.objects.create(
        restaurant=rest,
        category=cat,
        name='Garlic Bread',
        price=Decimal('100.00')
    )

    coupon_percent = Coupon.objects.create(
        code='SAVE50',
        discount_type='PERCENTAGE',
        discount_value=Decimal('50.00'),
        min_order_value=Decimal('150.00'),
        max_discount_amount=Decimal('50.00'),
        is_active=True
    )

    coupon_flat = Coupon.objects.create(
        code='FLAT30',
        discount_type='FLAT',
        discount_value=Decimal('30.00'),
        min_order_value=Decimal('200.00'),
        is_active=True
    )

    return {
        'restaurant': rest,
        'item1': item1,
        'item2': item2,
        'coupon_percent': coupon_percent,
        'coupon_flat': coupon_flat,
    }


def test_haversine_and_delivery_fee():
    # CP (28.6315, 77.2167) to India Gate (28.6129, 77.2295) is approx 2.4 km
    dist = haversine_distance(28.6315, 77.2167, 28.6129, 77.2295)
    assert 2.0 <= dist <= 3.0

    # Distance <= 2km base fee is ₹30
    assert calculate_delivery_fee(1.5) == Decimal('30.00')
    # Distance 4km: 30 + (4-2)*10 = ₹50
    assert calculate_delivery_fee(4.0) == Decimal('50.00')


def test_price_calculator_without_coupon(pricing_setup):
    rest = pricing_setup['restaurant']
    item1 = pricing_setup['item1'] # effective price 180
    item2 = pricing_setup['item2'] # 100

    items_data = [
        {'menu_item': item1, 'quantity': 2}, # 360
        {'menu_item': item2, 'quantity': 1}, # 100
    ]
    # Subtotal = 460
    # Tax = 5% of 460 = 23.00
    # Delivery fee base = 30.00
    # Total = 460 + 23 + 30 = 513.00

    res = PriceCalculator.calculate(
        items_data=items_data,
        restaurant=rest,
        delivery_lat=28.6140,
        delivery_lng=77.2091
    )

    assert res['subtotal'] == Decimal('460.00')
    assert res['tax_amount'] == Decimal('23.00')
    assert res['delivery_fee'] == Decimal('30.00')
    assert res['discount_amount'] == Decimal('0.00')
    assert res['total_amount'] == Decimal('513.00')


def test_price_calculator_with_capped_coupon(pricing_setup):
    rest = pricing_setup['restaurant']
    item1 = pricing_setup['item1'] # 180

    items_data = [{'menu_item': item1, 'quantity': 2}] # Subtotal 360
    # Coupon SAVE50: 50% of 360 is 180, but capped at max 50.00
    res = PriceCalculator.calculate(
        items_data=items_data,
        restaurant=rest,
        coupon_code='SAVE50'
    )

    assert res['subtotal'] == Decimal('360.00')
    assert res['discount_amount'] == Decimal('50.00')
    assert res['coupon'].code == 'SAVE50'


def test_dine_in_table_order_zero_delivery_fee(pricing_setup):
    rest = pricing_setup['restaurant']
    item1 = pricing_setup['item1']

    items_data = [{'menu_item': item1, 'quantity': 1}] # 180.00
    res = PriceCalculator.calculate(
        items_data=items_data,
        restaurant=rest,
        is_dine_in=True
    )
    # Dine-In orders MUST have 0 delivery fee
    assert res['delivery_fee'] == Decimal('0.00')
    assert res['subtotal'] == Decimal('180.00')
    assert res['tax_amount'] == Decimal('9.00') # 5% of 180
    assert res['total_amount'] == Decimal('189.00')

