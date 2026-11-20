import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

class OrderTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live order tracking page.
    Customer receives real-time status transitions and driver coordinates.
    """
    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = f"order_{self.order_id}"
        user = self.scope.get('user')

        # Check authorization
        can_access = await self.check_order_permission(user, self.order_id)
        if not can_access:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Clients typically only receive data on this channel
        pass

    async def order_status_update(self, event):
        """Handler for 'order_status_update' group messages."""
        await self.send(text_data=json.dumps(event))

    async def driver_location_update(self, event):
        """Handler for 'driver_location_update' coordinates broadcast."""
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def check_order_permission(self, user, order_id):
        from apps.orders.models import Order
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            # For guest/demo testing, if user is not logged in we still allow if order exists
            return Order.objects.filter(id=order_id).exists()
        
        # Staff and admins can always inspect orders
        if user.is_superuser or user.role in ['admin', 'kitchen_staff', 'delivery_partner']:
            return True

        # Customer must own the order
        return Order.objects.filter(id=order_id, customer=user).exists()


class KitchenKdsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the kitchen KDS screen.
    Streams new incoming orders and state changes in real-time.
    """
    async def connect(self):
        self.restaurant_id = self.scope['url_route']['kwargs']['restaurant_id']
        self.room_group_name = f"kitchen_{self.restaurant_id}"
        user = self.scope.get('user')

        # Role verification
        if not user or not user.is_authenticated:
            await self.close(code=4003)
            return

        if not (user.is_superuser or user.role in ['kitchen_staff', 'admin']):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def order_status_update(self, event):
        await self.send(text_data=json.dumps(event))


class DeliveryPartnerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for delivery partners to get real-time broadcasts of available ready orders.
    """
    async def connect(self):
        self.room_group_name = "delivery_partners"
        user = self.scope.get('user')

        if not user or not user.is_authenticated or user.role not in ['delivery_partner', 'admin']:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def order_status_update(self, event):
        await self.send(text_data=json.dumps(event))


class AdminConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live admin monitoring.
    """
    async def connect(self):
        self.room_group_name = "admin"
        user = self.scope.get('user')

        if not user or not user.is_authenticated or not (user.is_superuser or user.role == 'admin'):
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def order_status_update(self, event):
        await self.send(text_data=json.dumps(event))

