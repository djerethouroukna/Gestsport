from django import template
from django.db.models import Q

register = template.Library()

@register.filter
def unread_count(user):
    """Compte les notifications non lues pour un utilisateur"""
    return user.notifications.filter(is_read=False).count()

@register.simple_tag
def get_unread_notifications(user, limit=5):
    """Retourne les notifications non lues d'un utilisateur"""
    return user.notifications.filter(is_read=False).order_by('-created_at')[:limit]

@register.simple_tag  
def get_recent_notifications(user, limit=5):
    """Retourne les notifications récentes d'un utilisateur"""
    return user.notifications.all().order_by('-created_at')[:limit]
