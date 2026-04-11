# activities/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from events.models import BaseEvent

class ActivityType(models.TextChoices):
    TRAINING = 'training', _('Entraînement')
    MATCH = 'match', _('Match')
    TOURNAMENT = 'tournament', _('Tournoi')
    OTHER = 'other', _('Autre')

class ActivityStatus(models.TextChoices):
    PENDING = 'pending', _('En attente')
    CONFIRMED = 'confirmed', _('Confirmé')
    CANCELLED = 'cancelled', _('Annulé')
    COMPLETED = 'completed', _('Terminé')

class Activity(BaseEvent):
    """
    Modèle d'activité sportive héritant de BaseEvent
    Ajoute les champs spécifiques aux activités sportives
    """
    class Meta:
        verbose_name = _('activité')
        verbose_name_plural = _('activités')
        ordering = ['-start_time']

    # Champs spécifiques aux activités
    activity_type = models.CharField(
        _('type d\'activité'),
        max_length=20,
        choices=ActivityType.choices
    )
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coach_activities',
        verbose_name=_('entraîneur')
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='participating_activities',
        blank=True,
        verbose_name=_('participants')
    )
    max_participants = models.PositiveIntegerField(
        _('nombre maximum de participants')
    )
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=ActivityStatus.choices,
        default=ActivityStatus.PENDING
    )

    def __str__(self):
        return f"{self.title} - {self.get_activity_type_display()}"

    @property
    def available_spots(self):
        """Retourne le nombre de places disponibles"""
        return self.max_participants - self.participants.count()

    @property
    def is_full(self):
        """Vérifie si l'activité est complète"""
        return self.participants.count() >= self.max_participants

    @property
    def registration_open(self):
        """Vérifie si les inscriptions sont ouvertes"""
        from django.utils import timezone
        return (
            self.status == ActivityStatus.CONFIRMED and 
            not self.is_full and 
            not self.is_past
        )

    @property
    def participation_rate(self):
        """Retourne le taux de participation en pourcentage"""
        if self.max_participants > 0:
            return (self.participants.count() / self.max_participants) * 100
        return 0

    def create_reservation(self):
        """Crée automatiquement une réservation liée à cette activité"""
        from reservations.models import Reservation, ReservationStatus
        try:
            # Vérifier si une réservation existe déjà
            if hasattr(self, 'reservation'):
                return self.reservation
            
            # Créer la réservation
            reservation = Reservation.objects.create(
                user=self.coach,
                terrain=self.terrain,
                start_time=self.start_time,
                end_time=self.end_time,
                status=ReservationStatus.CONFIRMED if self.status == 'confirmed' else ReservationStatus.PENDING,
                notes=f"Réservation automatique pour l'activité: {self.title}"
            )
            
            # Lier l'activité à la réservation
            self.reservation = reservation
            self.save()
            
            return reservation
        except Exception as e:
            print(f"Erreur lors de la création de la réservation: {e}")
            return None

    @property
    def reservation(self):
        """Retourne la réservation liée à cette activité"""
        from reservations.models import Reservation
        try:
            return Reservation.objects.filter(
                terrain=self.terrain,
                start_time=self.start_time,
                end_time=self.end_time,
                user=self.coach
            ).first()
        except Exception:
            return None