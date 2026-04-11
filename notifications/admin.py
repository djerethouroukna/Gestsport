from django.contrib import admin
from .models import Notification, NotificationPreference

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'priority', 'is_read', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_read', 'created_at')
    search_fields = ('title', 'recipient__first_name', 'recipient__last_name', 'recipient__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'read_at')
    
    fieldsets = (
        ('Informations principales', {
            'fields': ('recipient', 'title', 'message')
        }),
        ('Classification', {
            'fields': ('notification_type', 'priority', 'is_read')
        }),
        ('Référence', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} notifications marquées comme lues.")
    mark_as_read.short_description = "Marquer comme lues"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"{queryset.count()} notifications marquées comme non lues.")
    mark_as_unread.short_description = "Marquer comme non lues"

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'email_enabled', 'push_enabled', 'in_app_enabled')
    list_filter = ('notification_type', 'email_enabled', 'push_enabled', 'in_app_enabled')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    ordering = ('user', 'notification_type')
    
    fieldsets = (
        ('Utilisateur et type', {
            'fields': ('user', 'notification_type')
        }),
        ('Canaux de notification', {
            'fields': ('email_enabled', 'push_enabled', 'in_app_enabled')
        }),
    )
