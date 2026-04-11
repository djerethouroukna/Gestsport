# events/models.py - VERSION CORRIGÉE
from django.db import models
from django.core.exceptions import ValidationError  # CORRECTION 1
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class BaseEvent(models.Model):
    """
    Modèle de base pour les événements (activités et réservations)
    Contient les champs communs à tous les types d'événements
    """
    class Meta:
        abstract = True  # Ne crée pas de table en base de données
        ordering = ['-start_time']

    # Champs communs
    title = models.CharField(_('titre'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='%(class)s_events',
        verbose_name=_('terrain')
    )
    start_time = models.DateTimeField(_('date et heure de début'))
    end_time = models.DateTimeField(_('date et heure de fin'))
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.terrain.name}"

    @property
    def duration(self):
        """Retourne la durée de l'événement"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def duration_hours(self):
        """Retourne la durée en heures"""
        if self.duration:
            return self.duration.total_seconds() / 3600
        return 0

    @property
    def is_past(self):
        """Vérifie si l'événement est passé"""
        from django.utils import timezone
        return self.end_time < timezone.now()

    @property
    def is_future(self):
        """Vérifie si l'événement est à venir"""
        from django.utils import timezone
        return self.start_time > timezone.now()

    @property
    def is_ongoing(self):
        """Vérifie si l'événement est en cours"""
        from django.utils import timezone
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    def clean(self):
        """Validation du modèle"""
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError({  # CORRECTION 2
                    'end_time': _('La date de fin doit être postérieure à la date de début.')
                })

    class Meta:
        abstract = True
        ordering = ['-start_time']
