import json
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class SyncConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        self.room_group = f"room_{self.room_code}"
        
        # Last sync time for throttling
        self.last_sync_time = 0
        self.listener_id = None

        await self.channel_layer.group_add(
            self.room_group,
            self.channel_name,
        )
        await self.accept()

        # Increment listener count
        count = await self.modify_listener_count(1)
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "sync_message",
                "message": {
                    "event": "listener_count",
                    "data": {"listener_count": count}
                },
            },
        )

    async def disconnect(self, close_code):
        # Remove listener from database if we have a listener_id
        await self.remove_listener()

        # Decrement listener count
        count = await self.modify_listener_count(-1)
        
        # Fetch updated roster
        listeners = await self.get_serialized_listeners()

        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "sync_message",
                "message": {
                    "event": "listener_count",
                    "data": {
                        "listener_count": count,
                        "listeners": listeners
                    }
                },
            },
        )
        await self.channel_layer.group_discard(
            self.room_group,
            self.channel_name,
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_type = data.get("type", data.get("event"))
        event_data = data.get("data", data)
        
        # Capture listener ID from incoming event
        if event_type in ("join_room", "listener_ready") and "listener_id" in event_data:
            self.listener_id = event_data["listener_id"]
            
            # Broadcast the updated listeners list so the broadcaster updates immediately
            listeners = await self.get_serialized_listeners()
            await self.channel_layer.group_send(
                self.room_group,
                {
                    "type": "sync_message",
                    "message": {
                        "event": "listener_count",
                        "data": {
                            "listener_count": await self.get_listener_count(),
                            "listeners": listeners
                        }
                    },
                },
            )

        # Prevent spam: throttle sync_state to once every 2 seconds
        # Other critical events (play, pause, webrtc, load_video, broadcast_message) bypass throttling.
        if event_type == "sync_state":
            now = time.time()
            if now - self.last_sync_time < 2.0:
                return
            self.last_sync_time = now

        # Broadcast the message to the group
        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "sync_message",
                "message": data,
            },
        )

    async def sync_message(self, event):
        await self.send(
            text_data=json.dumps(event["message"])
        )

    @database_sync_to_async
    def modify_listener_count(self, delta):
        from .models import Room
        try:
            room = Room.objects.get(room_code=self.room_code)
            room.listener_count = max(0, room.listener_count + delta)
            room.save(update_fields=['listener_count'])
            return room.listener_count
        except Room.DoesNotExist:
            return 0

    @database_sync_to_async
    def remove_listener(self):
        from .models import Listener
        if self.listener_id:
            try:
                import uuid
                lid = uuid.UUID(str(self.listener_id))
                Listener.objects.filter(listener_id=lid).delete()
            except Exception:
                pass

    @database_sync_to_async
    def get_serialized_listeners(self):
        from .models import Room
        from .serializers import ListenerSerializer
        try:
            room = Room.objects.get(room_code=self.room_code)
            return ListenerSerializer(room.listeners.all(), many=True).data
        except Room.DoesNotExist:
            return []

    @database_sync_to_async
    def get_listener_count(self):
        from .models import Room
        try:
            room = Room.objects.get(room_code=self.room_code)
            return room.listener_count
        except Room.DoesNotExist:
            return 0

