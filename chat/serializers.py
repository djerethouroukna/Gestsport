from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class ChatRoomSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les salons de chat"""
    participants_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'room_type', 'participants_count',
            'last_message', 'created_by', 'created_by_name',
            'last_activity', 'created_at'
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'last_activity')
    
    def get_participants_count(self, obj):
        return obj.participants.count()
    
    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-created_at').first()
        if last_message:
            return {
                'id': last_message.id,
                'content': last_message.content[:100],
                'author': last_message.author.get_full_name(),
                'created_at': last_message.created_at
            }
        return None

class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un salon de chat"""
    
    class Meta:
        model = ChatRoom
        fields = ('name', 'room_type')
    
    def create(self, validated_data):
        user = self.context['request'].user
        chatroom = ChatRoom.objects.create(
            created_by=user,
            **validated_data
        )
        # Le créateur est automatiquement ajouté comme participant
        chatroom.participants.add(user)
        return chatroom

class ChatRoomDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les détails d'un salon de chat"""
    participants = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'room_type', 'participants', 'messages',
            'created_by', 'created_by_name', 'last_activity', 'created_at'
        )
    
    def get_participants(self, obj):
        participants = obj.participants.all()
        return [
            {
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'role': user.role,
                'profile_picture': user.profile_picture.url if user.profile_picture else None
            }
            for user in participants
        ]
    
    def get_messages(self, obj):
        messages = obj.messages.order_by('-created_at')[:50]  # Derniers 50 messages
        return [
            {
                'id': msg.id,
                'content': msg.content,
                'author': msg.author.get_full_name(),
                'author_id': msg.author.id,
                'created_at': msg.created_at,
                'is_mine': msg.author == self.context['request'].user
            }
            for msg in messages
        ]

class MessageSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les messages"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    is_mine = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = (
            'id', 'content', 'author', 'author_name', 'is_mine',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'author', 'created_at', 'updated_at')
    
    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.author == request.user
        return False

class MessageCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un message"""
    
    class Meta:
        model = Message
        fields = ('content', 'chatroom')
    
    def validate(self, attrs):
        """Valider que l'utilisateur peut envoyer un message dans ce salon"""
        user = self.context['request'].user
        chatroom = attrs['chatroom']
        
        if not chatroom.participants.filter(id=user.id).exists():
            raise serializers.ValidationError("Vous n'êtes pas dans ce salon.")
        
        return attrs
    
    def create(self, validated_data):
        user = self.context['request'].user
        message = Message.objects.create(
            author=user,
            **validated_data
        )
        
        # Mettre à jour la dernière activité du salon
        chatroom = message.chatroom
        chatroom.last_activity = message.created_at
        chatroom.save()
        
        return message

class MessageListSerializer(serializers.ModelSerializer):
    """Sérialiseur pour lister les messages"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    is_mine = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ('id', 'content', 'author_name', 'is_mine', 'created_at')
    
    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.author == request.user
        return False

class DirectMessageSerializer(serializers.Serializer):
    """Sérialiseur pour créer un message direct"""
    user_id = serializers.IntegerField()
    initial_message = serializers.CharField(max_length=1000, required=False)

class ChatRoomSearchSerializer(serializers.Serializer):
    """Sérialiseur pour la recherche de salons"""
    query = serializers.CharField(required=False, allow_blank=True)
    room_type = serializers.ChoiceField(
        choices=ChatRoom.RoomType.choices,
        required=False
    )
    has_unread = serializers.BooleanField(required=False)
