import pytest
import json
from decimal import Decimal
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from food_delivery_backend.asgi import application
from apps.restaurants.models import Restaurant
from apps.orders.models import Order
from apps.notifications.consumers import OrderTrackingConsumer, KitchenKdsConsumer

User = get_user_model()

@pytest.mark.asyncio
async def test_order_tracking_consumer_communicator(db):
    cust = await User.objects.acreate(email='ws_cust@quickbite.com', role='customer')
    rest = await Restaurant.objects.acreate(name='WS Bistro', address='Main Ave', phone='112233')
    order = await Order.objects.acreate(
        order_number='QB-WS001',
        customer=cust,
        restaurant=rest,
        status='placed',
        subtotal=Decimal('200.00'),
        delivery_fee=Decimal('30.00'),
        total_amount=Decimal('230.00'),
        delivery_address_text='WS Street 1'
    )

    communicator = WebsocketCommunicator(
        application,
        f"/ws/orders/{order.id}/"
    )
    communicator.scope['user'] = cust

    connected, subprotocol = await communicator.connect()
    assert connected

    # Send a mock group message
    await communicator.send_to(text_data=json.dumps({'ping': 'pong'}))
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_kitchen_kds_rejects_unauthenticated_or_customer(db):
    rest = await Restaurant.objects.acreate(name='Kitchen Rest', address='Kitchen St', phone='998877')
    cust = await User.objects.acreate(email='cust_no_kds@quickbite.com', role='customer')

    # 1. Customer attempting to connect to KDS websocket
    communicator = WebsocketCommunicator(
        application,
        f"/ws/kitchen/{rest.id}/"
    )
    communicator.scope['user'] = cust

    connected, _ = await communicator.connect()
    assert not connected # Must reject connection!

