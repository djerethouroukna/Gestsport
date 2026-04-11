# chat/admin.py
from django.contrib import admin
from .models import Conversation, Message, ChatRoom

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'participants_count', 'created_by', 'last_activity', 'created_at')
    list_filter = ('room_type', 'created_at')
    search_fields = ('name', 'participants__email', 'participants__first_name', 'participants__last_name')
    readonly_fields = ('created_at',)
    filter_horizontal = ('participants',)
    
    def participants_count(self, obj):
        return obj.participants.count()
    participants_count.short_description = 'Participants'

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('participants__email', 'participants__first_name', 'participants__last_name')
    
    def get_participants(self, obj):
        return ", ".join([user.get_full_name() or user.email for user in obj.participants.all()])
    get_participants.short_description = 'Participants'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chatroom', 'author', 'content_preview', 'created_at', 'is_edited')
    list_filter = ('created_at', 'is_edited')
    search_fields = ('author__email', 'content')
    readonly_fields = ('created_at', 'updated_at')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Contenu'
    
    def has_add_permission(self, request):
        return False