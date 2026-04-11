# chat/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class ChatRoom(models.Model):
    class RoomType(models.TextChoices):
        GROUP = 'group', _('Groupe')
        DIRECT = 'direct', _('Message direct')
        ACTIVITY = 'activity', _('Activité')
    
    class Meta:
        verbose_name = _('salon de chat')
        verbose_name_plural = _('salons de chat')
        ordering = ['-last_activity']

    name = models.CharField(_('nom'), max_length=200)
    room_type = models.CharField(
        _('type de salon'),
        max_length=20,
        choices=RoomType.choices,
        default=RoomType.GROUP
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chatrooms',
        verbose_name=_('participants')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_chatrooms',
        verbose_name=_('créé par')
    )
    last_activity = models.DateTimeField(_('dernière activité'), null=True, blank=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)

    def __str__(self):
        return self.name

class Message(models.Model):
    class Meta:
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        ordering = ['created_at']

    chatroom = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('salon')
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('auteur')
    )
    content = models.TextField(_('contenu'))
    created_at = models.DateTimeField(_('date et heure'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)
    is_edited = models.BooleanField(_('modifié'), default=False)
    read = models.BooleanField(_('lu'), default=False)

    def __str__(self):
        return f"Message de {self.author} dans {self.chatroom.name}"

# Garder les anciens modèles pour compatibilité
class Conversation(models.Model):
    class Meta:
        verbose_name = _('conversation')
        verbose_name_plural = _('conversations')
        ordering = ['-updated_at']

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        verbose_name=_('participants')
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Conversation {self.id}"