# gather/notifications/consumers.py
from __future__ import annotations

import json

from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """Un utilisateur connecté rejoint son groupe personnel de
    notifications. Chaque NotificationService.creer() pour cet
    utilisateur sera poussé instantanément sur ce canal."""

    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close()
            return

        self.groupe = f"notifications_user_{user.id}"
        await self.channel_layer.group_add(self.groupe, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "groupe"):
            await self.channel_layer.group_discard(self.groupe, self.channel_name)

    async def notification_message(self, event):
        """Reçoit l'événement envoyé par group_send() et le transmet au
        client WebSocket connecté."""
        await self.send(text_data=json.dumps(event["notification"]))
