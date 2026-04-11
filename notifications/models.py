from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationType(models.TextChoices):
    RESERVATION_PENDING = 'reservation_pending', _('Nouvelle réservation en attente')
    RESERVATION_CONFIRMED = 'reservation_confirmed', _('Réservation confirmée')
    RESERVATION_REJECTED = 'reservation_rejected', _('Réservation rejetée')
    RESERVATION_CANCELLED = 'reservation_cancelled', _('Réservation annulée')
    ACTIVITY_REMINDER = 'activity_reminder', _('Rappel d\'activité')
    ACTIVITY_CANCELLED = 'activity_cancelled', _('Activité annulée')
    ACTIVITY_MODIFIED = 'activity_modified', _('Activité modifiée')
    PAYMENT_SUBMISSION = 'payment_submission', _('Nouvelle soumission de paiement')
    PAYMENT_VALIDATED = 'payment_validated', _('Paiement validé')
    PAYMENT_REJECTED = 'payment_rejected', _('Paiement rejeté')
    COACH_PAYMENT = 'coach_payment', _('Paiement entraîneur')
    SYSTEM_MESSAGE = 'system_message', _('Message système')

class NotificationPriority(models.TextChoices):
    LOW = 'low', _('Faible')
    MEDIUM = 'medium', _('Moyenne')
    HIGH = 'high', _('Haute')
    URGENT = 'urgent', _('Urgente')

class Notification(models.Model):
    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('destinataire')
    )
    title = models.CharField(_('titre'), max_length=200)
    message = models.TextField(_('message'))
    notification_type = models.CharField(
        _('type de notification'),
        max_length=30,
        choices=NotificationType.choices
    )
    priority = models.CharField(
        _('priorité'),
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.MEDIUM
    )
    is_read = models.BooleanField(_('lue'), default=False)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    read_at = models.DateTimeField(_('date de lecture'), null=True, blank=True)
    
    # Référence optionnelle à l'objet concerné
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """Marquer la notification comme lue"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class NotificationPreference(models.Model):
    """Préférences de notification par utilisateur"""
    class Meta:
        verbose_name = _('préférence de notification')
        verbose_name_plural = _('préférences de notification')
        unique_together = ['user', 'notification_type']

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('utilisateur')
    )
    notification_type = models.CharField(
        _('type de notification'),
        max_length=30,
        choices=NotificationType.choices
    )
    email_enabled = models.BooleanField(_('notification par email'), default=True)
    push_enabled = models.BooleanField(_('notification push'), default=True)
    in_app_enabled = models.BooleanField(_('notification in-app'), default=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_notification_type_display()}"
