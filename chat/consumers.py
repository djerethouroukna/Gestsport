import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # Vérifier que l'utilisateur est authentifié et a accès au salon
        if not self.scope['user'].is_authenticated:
            await self.close()
            return
        
        # Vérifier l'accès au salon
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return
        
        # Rejoindre le groupe
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notifier les autres utilisateurs
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_connected',
                'user': self.scope['user'].username,
                'user_id': self.scope['user'].id,
            }
        )
    
    async def disconnect(self, close_code):
        # Quitter le groupe
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notifier les autres utilisateurs
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_disconnected',
                'user': self.scope['user'].username,
                'user_id': self.scope['user'].id,
            }
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'new_message':
            await self.handle_new_message(data)
        elif message_type == 'typing':
            await self.handle_typing(data)
        elif message_type == 'stop_typing':
            await self.handle_stop_typing(data)
    
    async def handle_new_message(self, data):
        content = data.get('content', '').strip()
        
        if not content:
            return
        
        # Créer le message en base
        message = await self.create_message(content)
        
        # Envoyer le message au groupe
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'new_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'author_id': message.author.id,
                    'author_name': message.author.get_full_name() or message.author.username,
                    'author_username': message.author.username,
                    'created_at': message.created_at.isoformat(),
                    'is_edited': message.is_edited,
                }
            }
        )
        
        # Mettre à jour la dernière activité du salon
        await self.update_room_activity()
    
    async def handle_typing(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing',
                'is_typing': True,
                'user_id': self.scope['user'].id,
                'user_name': self.scope['user'].get_full_name() or self.scope['user'].username,
            }
        )
    
    async def handle_stop_typing(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing',
                'is_typing': False,
                'user_id': self.scope['user'].id,
                'user_name': self.scope['user'].get_full_name() or self.scope['user'].username,
            }
        )
    
    async def new_message(self, event):
        message = event['message']
        
        # Envoyer le message au WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': message
        }))
    
    async def typing(self, event):
        # Envoyer l'indicateur de frappe
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing'],
            'user_id': event['user_id'],
            'user_name': event['user_name'],
        }))
    
    async def user_connected(self, event):
        # Envoyer la notification de connexion
        await self.send(text_data=json.dumps({
            'type': 'user_connected',
            'user': event['user'],
            'user_id': event['user_id'],
        }))
    
    async def user_disconnected(self, event):
        # Envoyer la notification de déconnexion
        await self.send(text_data=json.dumps({
            'type': 'user_disconnected',
            'user': event['user'],
            'user_id': event['user_id'],
        }))
    
    @database_sync_to_async
    def check_room_access(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.participants.filter(id=self.scope['user'].id).exists()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message(self, content):
        room = ChatRoom.objects.get(id=self.room_id)
        message = Message.objects.create(
            chatroom=room,
            author=self.scope['user'],
            content=content
        )
        return message
    
    @database_sync_to_async
    def update_room_activity(self):
        from django.utils import timezone
        room = ChatRoom.objects.get(id=self.room_id)
        room.last_activity = timezone.now()
        room.save()
