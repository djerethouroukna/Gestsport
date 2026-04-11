# reservations/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from events.models import BaseEvent
from terrains.models import Terrain

class ReservationStatus(models.TextChoices):
    PENDING = 'pending', _('En attente')
    CONFIRMED = 'confirmed', _('Confirmée')
    REJECTED = 'rejected', _('Rejetée')
    CANCELLED = 'cancelled', _('Annulée')
    COMPLETED = 'completed', _('Terminée')

class PaymentStatus(models.TextChoices):
    PENDING = 'pending', _('En attente')
    PAID = 'paid', _('Payé')
    REFUNDED = 'refunded', _('Remboursé')
    FAILED = 'failed', _('Échoué')

class Reservation(BaseEvent):
    """
    Modèle de réservation héritant de BaseEvent
    Ajoute les champs spécifiques aux réservations
    """
    class Meta:
        verbose_name = _('réservation')
        verbose_name_plural = _('réservations')
        ordering = ['-start_time']

    # Champs spécifiques aux réservations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name=_('utilisateur')
    )
    terrain = models.ForeignKey(
        Terrain,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name=_('terrain')
    )
    start_time = models.DateTimeField(_('date et heure de début'))
    end_time = models.DateTimeField(_('date et heure de fin'))
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING
    )
    notes = models.TextField(_('notes'), blank=True)
    
    # Override du champ title pour le rendre optionnel pour les réservations
    title = models.CharField(_('titre'), max_length=200, blank=True, default='')
    
    # Champs financiers
    total_amount = models.DecimalField(
        _('montant total'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    price_per_hour = models.DecimalField(
        _('prix par heure'),
        max_digits=8,
        decimal_places=2,
        default=0
    )
    payment_status = models.CharField(
        _('statut de paiement'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    payment_method = models.CharField(
        _('méthode de paiement'),
        max_length=20,
        blank=True,
        choices=[
            ('cash', 'Espèces'),
            ('card', 'Carte bancaire'),
            ('mobile_money', 'Mobile Money'),
            ('transfer', 'Virement bancaire')
        ]
    )
    payment_date = models.DateTimeField(
        _('date de paiement'),
        null=True,
        blank=True
    )
    transaction_id = models.CharField(
        _('identifiant de transaction'),
        max_length=100,
        blank=True
    )
    
    # Validation et confirmation
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_reservations',
        verbose_name=_('confirmé par')
    )
    confirmation_date = models.DateTimeField(
        _('date de confirmation'),
        null=True,
        blank=True
    )
    
    # Liaison avec activité (optionnel)
    activity = models.ForeignKey(
        'activities.Activity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        verbose_name=_('activité liée')
    )

    def __str__(self):
        return f"Réservation de {self.terrain.name} par {self.user.get_full_name() or self.user.username}"

    @property
    def has_payment(self):
        """Vérifie si la réservation a un paiement associé"""
        return hasattr(self, 'payment') and self.payment is not None

    @property
    def is_paid(self):
        """Vérifie si la réservation est payée"""
        return self.has_payment and self.payment.is_paid

    @property
    def payment_status(self):
        """Retourne le statut du paiement"""
        if not self.has_payment:
            return None
        return self.payment.status

    def calculate_total_amount(self):
        """Calcule le montant total de la réservation"""
        from decimal import Decimal
        
        # Si c'est une réservation d'activité, utiliser le prix de l'activité
        if self.is_activity_reservation:
            activity = self.linked_activity
            if activity:
                # Prix par défaut pour les activités (peut être personnalisé)
                return Decimal('50.00')  # Prix fixe par défaut
        
        # Calcul standard pour les réservations normales
        duration = self.end_time - self.start_time
        hours = Decimal(str(duration.total_seconds() / 3600))
        
        # Prix par heure : utiliser le prix du terrain s'il existe, sinon prix par défaut
        if hasattr(self.terrain, 'price_per_hour') and self.terrain.price_per_hour:
            hourly_rate = self.terrain.price_per_hour
        else:
            hourly_rate = Decimal('20.00')  # Prix par défaut
        
        return hours * hourly_rate

    @property
    def linked_activity(self):
        """Retourne l'activité liée à cette réservation"""
        from activities.models import Activity
        try:
            return Activity.objects.filter(
                terrain=self.terrain,
                start_time=self.start_time,
                end_time=self.end_time,
                coach=self.user
            ).first()
        except Exception:
            return None

    @property
    def is_activity_reservation(self):
        """Vérifie si cette réservation est pour une activité"""
        return self.linked_activity is not None

    @property
    def reservation_type(self):
        """Retourne le type de réservation"""
        if self.is_activity_reservation:
            activity = self.linked_activity
            return f"Activité: {activity.get_activity_type_display()}"
        return "Réservation standard"

    @property
    def can_be_paid(self):
        """Vérifie si la réservation peut être payée"""
        return (
            self.status in ['pending', 'confirmed'] and
            not self.has_payment
        )

    @property
    def has_payment_submission(self):
        """Vérifie si la réservation a une soumission de paiement"""
        return hasattr(self, 'payment_submission')

    @property
    def payment_submission_status(self):
        """Retourne le statut de la soumission de paiement"""
        if not self.has_payment_submission:
            return None
        return self.payment_submission.status

    @property
    def is_payment_pending_validation(self):
        """Vérifie si le paiement est en attente de validation"""
        return self.has_payment_submission and self.payment_submission.is_pending_validation

    @property
    def is_payment_validated(self):
        """Vérifie si le paiement a été validé"""
        return self.has_payment_submission and self.payment_submission.is_validated

    @property
    def is_payment_rejected(self):
        """Vérifie si le paiement a été rejeté"""
        return self.has_payment_submission and self.payment_submission.is_rejected

    @property
    def payment_status_display(self):
        """Retourne le statut de paiement affiché"""
        if self.is_paid:
            return "Payé"
        elif self.is_payment_validated:
            return "Validé"
        elif self.is_payment_pending_validation:
            return "En attente de validation"
        elif self.is_payment_rejected:
            return "Rejeté"
        else:
            return "Non payé"

    @property
    def has_timeslot(self):
        """Vérifie si la réservation a un créneau horaire associé"""
        return hasattr(self, 'timeslot')

    @property
    def timeslot_status(self):
        """Retourne le statut du créneau horaire"""
        if not self.has_timeslot:
            return None
        return self.timeslot.status

    @property
    def effective_price(self):
        """Calcule le prix effectif avec les créneaux horaires"""
        if self.has_timeslot:
            from timeslots.services import TimeSlotService
            return TimeSlotService.get_timeslot_price(self.timeslot)
        return self.total_amount

    @property
    def duration_minutes(self):
        """Durée de la réservation en minutes"""
        duration = self.end_time - self.start_time
        return int(duration.total_seconds() / 60)

    def get_available_timeslots(self):
        """Récupère les créneaux disponibles pour cette réservation"""
        from timeslots.services import TimeSlotService

        return TimeSlotService.get_available_timeslots(
            terrain=self.terrain,
            target_date=self.start_time.date(),
            start_time=self.start_time.time(),
            end_time=self.end_time.time()
        )

    def check_timeslot_availability(self):
        """Vérifie la disponibilité des créneaux pour cette réservation"""
        from timeslots.services import TimeSlotService

        is_available, conflicting_slots = TimeSlotService.check_availability(
            terrain=self.terrain,
            start_datetime=self.start_time,
            end_datetime=self.end_time
        )

        return is_available, conflicting_slots