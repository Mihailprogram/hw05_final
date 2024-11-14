import json
from channels.generic.websocket import AsyncWebsocketConsumer

class LikeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("like_updates", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("like_updates", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        post_id = data["post_id"]
        count_likes = data["count_likes"]

        # Отправляем обновленные данные всем участникам группы
        await self.channel_layer.group_send(
            "like_updates",
            {
                "type": "send_like_update",
                "post_id": post_id,
                "count_likes": count_likes,
            },
        )

    async def send_like_update(self, event):
        await self.send(text_data=json.dumps({
            "post_id": event["post_id"],
            "count_likes": event["count_likes"],
        }))
