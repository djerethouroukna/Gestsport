from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, NotificationPreference, NotificationType, NotificationPriority

User = get_user_model()

class NotificationSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les notifications"""
    
    class Meta:
        model = Notification
        fields = (
            'id', 'title', 'message', 'notification_type', 'priority',
            'is_read', 'created_at', 'read_at', 'content_type', 'object_id'
        )
        read_only_fields = ('id', 'created_at', 'read_at')

class NotificationCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer des notifications"""
    
    class Meta:
        model = Notification
        fields = (
            'recipient', 'title', 'message', 'notification_type',
            'priority', 'content_type', 'object_id'
        )
    
    def validate_recipient(self, value):
        """Valider que le destinataire existe et est actif"""
        if not value.is_active:
            raise serializers.ValidationError("Le destinataire doit être un utilisateur actif.")
        return value

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les préférences de notification"""
    
    class Meta:
        model = NotificationPreference
        fields = (
            'id', 'user', 'notification_type', 'email_enabled',
            'push_enabled', 'in_app_enabled'
        )
        read_only_fields = ('id', 'user')

class NotificationPreferenceUpdateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour mettre à jour les préférences"""
    
    class Meta:
        model = NotificationPreference
        fields = ('email_enabled', 'push_enabled', 'in_app_enabled')

class NotificationListSerializer(serializers.ModelSerializer):
    """Sérialiseur pour lister les notifications avec moins de détails"""
    
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = (
            'id', 'title', 'notification_type', 'notification_type_display',
            'priority', 'priority_display', 'is_read', 'created_at'
        )

class UnreadCountSerializer(serializers.Serializer):
    """Sérialiseur pour le compteur de notifications non lues"""
    unread_count = serializers.IntegerField(read_only=True)
    total_count = serializers.IntegerField(read_only=True)

class BulkNotificationSerializer(serializers.Serializer):
    """Sérialiseur pour les actions en masse sur les notifications"""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=['mark_read', 'mark_unread', 'delete'])

class NotificationSearchSerializer(serializers.Serializer):
    """Sérialiseur pour la recherche de notifications"""
    query = serializers.CharField(required=False, allow_blank=True)
    notification_type = serializers.ChoiceField(
        choices=NotificationType.choices,
        required=False
    )
    priority = serializers.ChoiceField(
        choices=NotificationPriority.choices,
        required=False
    )
    is_read = serializers.BooleanField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
