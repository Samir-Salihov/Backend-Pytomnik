# apps/kanban/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class KanbanRealtimeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.board_id = self.scope["url_route"]["kwargs"]["board_id"]
        self.group_name = f"kanban_{self.board_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def card_moved(self, event):
        await self.send(text_data=json.dumps({
            "type": "CARD_MOVED",
            "payload": {
                "cardId": event["card_id"],
                "fromColumnId": event["from_column"],
                "toColumnId": event["to_column"],
                "position": event["position"]
            }
        }))