# waitinglist/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, date, time, timedelta
import uuid

User = get_user_model()


class WaitingListStatus(models.TextChoices):
    WAITING = 'waiting', _('En attente')
    NOTIFIED = 'notified', _('Notifié')
    ACCEPTED = 'accepted', _('Accepté')
    DECLINED = 'declined', _('Décliné')
    EXPIRED = 'expired', _('Expiré')
    CANCELLED = 'cancelled', _('Annulé')


class WaitingListPriority(models.TextChoices):
    LOW = 'low', _('Faible')
    NORMAL = 'normal', _('Normal')
    HIGH = 'high', _('Élevé')
    URGENT = 'urgent', _('Urgent')


class WaitingList(models.Model):
    """Liste d'attente pour les créneaux indisponibles"""
    class Meta:
        verbose_name = _('liste d\'attente')
        verbose_name_plural = _('listes d\'attente')
        ordering = ['terrain', 'date', 'priority', 'created_at']
        indexes = [
            models.Index(fields=['terrain', 'date', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['priority', 'created_at']),
        ]
        unique_together = ['user', 'terrain', 'date', 'start_time', 'end_time']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='waiting_list_entries',
        verbose_name=_('utilisateur')
    )
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='waiting_list_entries',
        verbose_name=_('terrain')
    )
    
    # Période souhaitée
    date = models.DateField(_('date souhaitée'))
    start_time = models.TimeField(_('heure de début souhaitée'))
    end_time = models.TimeField(_('heure de fin souhaitée'))
    duration_minutes = models.PositiveIntegerField(_('durée en minutes'))
    
    # Priorité et statut
    priority = models.CharField(
        _('priorité'),
        max_length=20,
        choices=WaitingListPriority.choices,
        default=WaitingListPriority.NORMAL
    )
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=WaitingListStatus.choices,
        default=WaitingListStatus.WAITING
    )
    
    # Préférences
    flexible_times = models.BooleanField(
        _('horaires flexibles'),
        default=True,
        help_text=_('Accepte des créneaux proches de l\'heure souhaitée')
    )
    max_time_difference = models.PositiveIntegerField(
        _('différence max d\'heure (minutes)'),
        default=60,
        help_text=_('Différence maximale acceptée par rapport à l\'heure souhaitée')
    )
    flexible_date = models.BooleanField(
        _('date flexible'),
        default=False,
        help_text=_('Accepte des dates proches de la date souhaitée')
    )
    max_date_difference = models.PositiveIntegerField(
        _('différence max de date (jours)'),
        default=0,
        help_text=_('Différence maximale acceptée par rapport à la date souhaitée')
    )
    
    # Notifications
    notification_sent_at = models.DateTimeField(
        _('date de notification'),
        null=True,
        blank=True
    )
    notification_expires_at = models.DateTimeField(
        _('expiration notification'),
        null=True,
        blank=True
    )
    notification_count = models.PositiveIntegerField(
        _('nombre de notifications'),
        default=0
    )
    
    # Réservation associée
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='waiting_list_entry',
        verbose_name=_('réservation associée')
    )
    
    # Notes
    notes = models.TextField(_('notes'), blank=True)
    admin_notes = models.TextField(_('notes admin'), blank=True)
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.terrain.name} - {self.date}"

    @property
    def is_active(self):
        """Vérifie si l'entrée est active"""
        return self.status == WaitingListStatus.WAITING

    @property
    def is_notified(self):
        """Vérifie si l'utilisateur a été notifié"""
        return self.status == WaitingListStatus.NOTIFIED

    @property
    def notification_expired(self):
        """Vérifie si la notification a expiré"""
        if not self.notification_expires_at:
            return False
        return timezone.now() > self.notification_expires_at

    @property
    def days_in_waiting(self):
        """Jours passés dans la liste d'attente"""
        return (timezone.now() - self.created_at).days

    def can_match_timeslot(self, timeslot) -> bool:
        """Vérifie si un créneau correspond aux préférences"""
        if not self.is_active:
            return False
        
        # Vérifier la date
        if timeslot.date != self.date:
            if not self.flexible_date:
                return False
            date_diff = abs((timeslot.date - self.date).days)
            if date_diff > self.max_date_difference:
                return False
        
        # Vérifier les heures
        if not self.flexible_times:
            return (timeslot.start_time == self.start_time and 
                   timeslot.end_time == self.end_time)
        
        # Vérifier la durée
        if timeslot.duration_minutes != self.duration_minutes:
            return False
        
        # Vérifier la différence d'heure
        start_diff = abs(
            (datetime.combine(timeslot.date, timeslot.start_time) - 
             datetime.combine(self.date, self.start_time)).total_seconds() / 60
        )
        
        return start_diff <= self.max_time_difference

    def notify_user(self, timeslot=None):
        """Notifie l'utilisateur qu'un créneau est disponible"""
        self.status = WaitingListStatus.NOTIFIED
        self.notification_sent_at = timezone.now()
        self.notification_expires_at = timezone.now() + timedelta(hours=24)
        self.notification_count += 1
        self.save()

    def accept_offer(self, reservation):
        """Accepte l'offre et crée la réservation"""
        self.status = WaitingListStatus.ACCEPTED
        self.reservation = reservation
        self.save()

    def decline_offer(self):
        """Décline l'offre"""
        self.status = WaitingListStatus.DECLINED
        self.save()

    def cancel(self):
        """Annule l'entrée dans la liste d'attente"""
        self.status = WaitingListStatus.CANCELLED
        self.save()


class WaitingListConfiguration(models.Model):
    """Configuration de la liste d'attente"""
    class Meta:
        verbose_name = _('configuration liste d\'attente')
        verbose_name_plural = _('configurations liste d\'attente')

    terrain = models.OneToOneField(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='waiting_list_config',
        verbose_name=_('terrain')
    )
    
    # Paramètres généraux
    is_enabled = models.BooleanField(_('activée'), default=True)
    max_entries_per_day = models.PositiveIntegerField(
        _('max entrées par jour'),
        default=50,
        help_text=_('Nombre maximum d\'entrées dans la liste d\'attente par jour')
    )
    
    # Paramètres de notification
    notification_hours_before = models.PositiveIntegerField(
        _('heures avant notification'),
        default=24,
        help_text=_('Nombre d\'heures avant le créneau pour notifier')
    )
    notification_expiry_hours = models.PositiveIntegerField(
        _('heures expiration notification'),
        default=24,
        help_text=_('Durée de validité de la notification')
    )
    max_notifications_per_user = models.PositiveIntegerField(
        _('max notifications par utilisateur'),
        default=3,
        help_text=_('Nombre maximum de notifications par utilisateur')
    )
    
    # Priorités automatiques
    enable_priority_scoring = models.BooleanField(
        _('scoring priorité automatique'),
        default=True
    )
    
    # Scores de priorité
    vip_score_bonus = models.PositiveIntegerField(
        _('bonus score VIP'),
        default=100
    )
    frequent_user_score_bonus = models.PositiveIntegerField(
        _('bonus score utilisateur fréquent'),
        default=50
    )
    long_waiting_score_bonus = models.PositiveIntegerField(
        _('bonus score longue attente'),
        default=10
    )
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Configuration {self.terrain.name}"


class WaitingListNotification(models.Model):
    """Historique des notifications de la liste d'attente"""
    class Meta:
        verbose_name = _('notification liste d\'attente')
        verbose_name_plural = _('notifications liste d\'attente')
        ordering = ['-sent_at']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    waiting_list_entry = models.ForeignKey(
        WaitingList,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('entrée liste d\'attente')
    )
    
    # Détails de la notification
    notification_type = models.CharField(
        _('type de notification'),
        max_length=50,
        choices=[
            ('timeslot_available', _('Créneau disponible')),
            ('reminder', _('Rappel')),
            ('expiry_warning', _('Avertissement expiration')),
        ]
    )
    
    # Créneau proposé
    proposed_timeslot_id = models.UUIDField(
        _('ID créneau proposé'),
        null=True,
        blank=True
    )
    proposed_date = models.DateField(
        _('date proposée'),
        null=True,
        blank=True
    )
    proposed_start_time = models.TimeField(
        _('heure début proposée'),
        null=True,
        blank=True
    )
    proposed_end_time = models.TimeField(
        _('heure fin proposée'),
        null=True,
        blank=True
    )
    
    # Statut
    sent_at = models.DateTimeField(_('date d\'envoi'), auto_now_add=True)
    read_at = models.DateTimeField(_('date de lecture'), null=True, blank=True)
    responded_at = models.DateTimeField(_('date de réponse'), null=True, blank=True)
    
    # Réponse
    response = models.CharField(
        _('réponse'),
        max_length=20,
        choices=[
            ('accepted', _('Accepté')),
            ('declined', _('Décliné')),
            ('expired', _('Expiré')),
        ],
        null=True,
        blank=True
    )
    
    # Message
    message = models.TextField(_('message'))
    response_message = models.TextField(_('message réponse'), blank=True)

    def __str__(self):
        return f"Notification {self.waiting_list_entry.user.get_full_name()} - {self.notification_type}"

    @property
    def is_read(self):
        """Vérifie si la notification a été lue"""
        return self.read_at is not None

    @property
    def is_responded(self):
        """Vérifie si la notification a reçu une réponse"""
        return self.response is not None

    @property
    def response_time_minutes(self):
        """Temps de réponse en minutes"""
        if not self.responded_at or not self.sent_at:
            return None
        return int((self.responded_at - self.sent_at).total_seconds() / 60)


class WaitingListStatistics(models.Model):
    """Statistiques de la liste d'attente"""
    class Meta:
        verbose_name = _('statistiques liste d\'attente')
        verbose_name_plural = _('statistiques liste d\'attente')
        ordering = ['-date']
        unique_together = ['terrain', 'date']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='waiting_list_statistics',
        verbose_name=_('terrain')
    )
    date = models.DateField(_('date'))
    
    # Statistiques journalières
    total_entries = models.PositiveIntegerField(_('total entrées'), default=0)
    new_entries = models.PositiveIntegerField(_('nouvelles entrées'), default=0)
    resolved_entries = models.PositiveIntegerField(_('entrées résolues'), default=0)
    
    # Répartitions
    entries_by_priority = models.JSONField(
        _('entrées par priorité'),
        default=dict,
        blank=True
    )
    entries_by_status = models.JSONField(
        _('entrées par statut'),
        default=dict,
        blank=True
    )
    
    # Notifications
    notifications_sent = models.PositiveIntegerField(_('notifications envoyées'), default=0)
    notifications_accepted = models.PositiveIntegerField(_('notifications acceptées'), default=0)
    notifications_declined = models.PositiveIntegerField(_('notifications déclinées'), default=0)
    
    # Temps d'attente moyen
    avg_waiting_time_hours = models.DecimalField(
        _('temps d\'attente moyen (heures)'),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # Taux de conversion
    conversion_rate = models.DecimalField(
        _('taux de conversion'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0'),
        help_text=_('Pourcentage d\'entrées converties en réservations')
    )
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Stats {self.terrain.name} - {self.date}"
