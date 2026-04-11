# timeslots/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import uuid

User = get_user_model()


class TimeSlotStatus(models.TextChoices):
    AVAILABLE = 'available', _('Disponible')
    BOOKED = 'booked', _('Réservé')
    BLOCKED = 'blocked', _('Bloqué')
    MAINTENANCE = 'maintenance', _('Maintenance')
    UNAVAILABLE = 'unavailable', _('Indisponible')


class TimeSlot(models.Model):
    """Créneaux horaires pour les terrains"""
    class Meta:
        verbose_name = _('créneau horaire')
        verbose_name_plural = _('créneaux horaires')
        ordering = ['terrain', 'date', 'start_time']
        unique_together = ['terrain', 'date', 'start_time', 'end_time']
        indexes = [
            models.Index(fields=['terrain', 'date', 'status']),
            models.Index(fields=['date', 'start_time']),
            models.Index(fields=['status']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='timeslots',
        verbose_name=_('terrain')
    )
    date = models.DateField(_('date'))
    start_time = models.TimeField(_('heure de début'))
    end_time = models.TimeField(_('heure de fin'))
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=TimeSlotStatus.choices,
        default=TimeSlotStatus.AVAILABLE
    )
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeslot',
        verbose_name=_('réservation')
    )
    price_override = models.DecimalField(
        _('prix personnalisé'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Prix spécifique pour ce créneau (remplace le prix par défaut)')
    )
    is_recurring = models.BooleanField(_('récurrent'), default=False)
    recurring_pattern = models.JSONField(
        _('pattern de récurrence'),
        default=dict,
        blank=True,
        help_text=_('Configuration de la récurrence')
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.terrain.name} - {self.date} {self.start_time}-{self.end_time}"

    @property
    def duration_minutes(self):
        """Durée du créneau en minutes"""
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        return int((end - start).total_seconds() / 60)

    @property
    def duration_hours(self):
        """Durée du créneau en heures"""
        return self.duration_minutes / 60

    @property
    def is_available(self):
        """Vérifie si le créneau est disponible"""
        return self.status == TimeSlotStatus.AVAILABLE

    @property
    def can_be_booked(self):
        """Vérifie si le créneau peut être réservé"""
        return (
            self.is_available and
            not self.reservation and
            self.date >= datetime.now().date()
        )

    @property
    def effective_price(self):
        """Prix effectif du créneau"""
        if self.price_override:
            return self.price_override
        return self.terrain.price_per_hour * self.duration_hours

    def mark_as_booked(self, reservation):
        """Marque le créneau comme réservé"""
        self.status = TimeSlotStatus.BOOKED
        self.reservation = reservation
        self.save()

    def mark_as_available(self):
        """Marque le créneau comme disponible"""
        self.status = TimeSlotStatus.AVAILABLE
        self.reservation = None
        self.save()


class AvailabilityRule(models.Model):
    """Règles de disponibilité spéciales"""
    class Meta:
        verbose_name = _('règle de disponibilité')
        verbose_name_plural = _('règles de disponibilité')
        ordering = ['terrain', 'priority']

    RULE_TYPES = [
        ('block', _('Bloquer')),
        ('available', _('Rendre disponible')),
        ('price_override', _('Modifier le prix')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='availability_rules',
        verbose_name=_('terrain')
    )
    rule_type = models.CharField(
        _('type de règle'),
        max_length=20,
        choices=RULE_TYPES
    )
    name = models.CharField(_('nom'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    priority = models.PositiveIntegerField(
        _('priorité'),
        default=0,
        help_text=_('Plus la priorité est élevée, plus la règle est importante')
    )
    
    # Conditions temporelles
    start_date = models.DateField(_('date de début'), null=True, blank=True)
    end_date = models.DateField(_('date de fin'), null=True, blank=True)
    start_time = models.TimeField(_('heure de début'), null=True, blank=True)
    end_time = models.TimeField(_('heure de fin'), null=True, blank=True)
    
    # Jours de la semaine
    monday = models.BooleanField(_('lundi'), default=False)
    tuesday = models.BooleanField(_('mardi'), default=False)
    wednesday = models.BooleanField(_('mercredi'), default=False)
    thursday = models.BooleanField(_('jeudi'), default=False)
    friday = models.BooleanField(_('vendredi'), default=False)
    saturday = models.BooleanField(_('samedi'), default=False)
    sunday = models.BooleanField(_('dimanche'), default=False)
    
    # Action
    price_multiplier = models.DecimalField(
        _('multiplicateur de prix'),
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text=_('Multiplie le prix par défaut (ex: 1.5 pour +50%)')
    )
    price_override = models.DecimalField(
        _('prix fixe'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Prix fixe qui remplace le prix par défaut')
    )
    
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.terrain.name} - {self.name}"

    def applies_to_date(self, date):
        """Vérifie si la règle s'applique à une date"""
        # Vérifier les dates de début/fin
        if self.start_date and date < self.start_date:
            return False
        if self.end_date and date > self.end_date:
            return False
        
        # Vérifier le jour de la semaine
        weekday = date.weekday()  # 0 = lundi, 6 = dimanche
        day_fields = [
            self.monday, self.tuesday, self.wednesday,
            self.thursday, self.friday, self.saturday, self.sunday
        ]
        
        # Si aucun jour n'est coché, la règle s'applique tous les jours
        if not any(day_fields):
            return True
        
        return day_fields[weekday]

    def applies_to_time(self, time):
        """Vérifie si la règle s'applique à une heure"""
        if not self.start_time or not self.end_time:
            return True
        
        return self.start_time <= time <= self.end_time

    def get_adjusted_price(self, base_price):
        """Calcule le prix ajusté selon la règle"""
        if self.price_override:
            return self.price_override
        
        if self.price_multiplier != 1.00:
            return base_price * self.price_multiplier
        
        return base_price


class TimeSlotGeneration(models.Model):
    """Historique des générations de créneaux"""
    class Meta:
        verbose_name = _('génération de créneaux')
        verbose_name_plural = _('générations de créneaux')
        ordering = ['-created_at']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='slot_generations',
        verbose_name=_('terrain')
    )
    start_date = models.DateField(_('date de début'))
    end_date = models.DateField(_('date de fin'))
    slot_duration = models.PositiveIntegerField(
        _('durée des créneaux'),
        help_text=_('Durée en minutes')
    )
    slots_generated = models.PositiveIntegerField(_('nombre de créneaux générés'))
    generation_method = models.CharField(
        _('méthode de génération'),
        max_length=50,
        choices=[
            ('automatic', _('Automatique')),
            ('manual', _('Manuelle')),
            ('bulk', _('Massive')),
        ]
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='slot_generations',
        verbose_name=_('créé par')
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)

    def __str__(self):
        return f"Génération {self.terrain.name} du {self.start_date} au {self.end_date}"


class TimeSlotBlock(models.Model):
    """Blocages temporaires de créneaux"""
    class Meta:
        verbose_name = _('blocage de créneau')
        verbose_name_plural = _('blocages de créneaux')
        ordering = ['terrain', 'start_datetime']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='slot_blocks',
        verbose_name=_('terrain')
    )
    start_datetime = models.DateTimeField(_('date et heure de début'))
    end_datetime = models.DateTimeField(_('date et heure de fin'))
    reason = models.TextField(_('raison du blocage'))
    is_maintenance = models.BooleanField(_('maintenance'), default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='slot_blocks',
        verbose_name=_('créé par')
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)

    def __str__(self):
        return f"Blocage {self.terrain.name} du {self.start_datetime} au {self.end_datetime}"

    @property
    def affects_timeslots(self):
        """Retourne les créneaux affectés par ce blocage"""
        return TimeSlot.objects.filter(
            terrain=self.terrain,
            date__gte=self.start_datetime.date(),
            date__lte=self.end_datetime.date(),
            start_time__gte=self.start_datetime.time(),
            end_time__lte=self.end_datetime.time()
        )
