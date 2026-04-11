# subscriptions/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, date, time, timedelta
from typing import Tuple, List
import uuid

User = get_user_model()


class MembershipType(models.TextChoices):
    INDIVIDUAL = 'individual', _('Individuel')
    FAMILY = 'family', _('Familial')
    CORPORATE = 'corporate', _('Entreprise')
    STUDENT = 'student', _('Étudiant')
    SENIOR = 'senior', _('Senior')


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'active', _('Actif')
    INACTIVE = 'inactive', _('Inactif')
    SUSPENDED = 'suspended', _('Suspendu')
    CANCELLED = 'cancelled', _('Annulé')
    EXPIRED = 'expired', _('Expiré')


class RecurrenceType(models.TextChoices):
    DAILY = 'daily', _('Quotidien')
    WEEKLY = 'weekly', _('Hebdomadaire')
    MONTHLY = 'monthly', _('Mensuel')
    QUARTERLY = 'quarterly', _('Trimestriel')
    YEARLY = 'yearly', _('Annuel')


class Membership(models.Model):
    """Types d'abonnements disponibles"""
    class Meta:
        verbose_name = _('type d\'abonnement')
        verbose_name_plural = _('types d\'abonnements')
        ordering = ['name']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nom'), max_length=100)
    description = models.TextField(_('description'))
    membership_type = models.CharField(
        _('type d\'abonnement'),
        max_length=20,
        choices=MembershipType.choices
    )
    
    # Tarification
    base_price = models.DecimalField(
        _('prix de base'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(_('devise'), max_length=3, default='XOF')
    
    # Durée et récurrence
    duration_days = models.PositiveIntegerField(
        _('durée en jours'),
        help_text=_('Durée de l\'abonnement en jours')
    )
    recurrence_type = models.CharField(
        _('type de récurrence'),
        max_length=20,
        choices=RecurrenceType.choices,
        help_text=_('Type de renouvellement automatique')
    )
    
    # Avantages
    max_reservations_per_month = models.PositiveIntegerField(
        _('max réservations par mois'),
        null=True,
        blank=True,
        help_text=_('Nombre maximum de réservations incluses par mois')
    )
    max_reservations_per_week = models.PositiveIntegerField(
        _('max réservations par semaine'),
        null=True,
        blank=True,
        help_text=_('Nombre maximum de réservations incluses par semaine')
    )
    included_hours_per_month = models.PositiveIntegerField(
        _('heures incluses par mois'),
        null=True,
        blank=True,
        help_text=_('Nombre d\'heures incluses par mois')
    )
    
    # Réductions
    discount_percentage = models.DecimalField(
        _('pourcentage de réduction'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0'),
        help_text=_('Réduction appliquée sur les réservations')
    )
    free_cancellation_hours = models.PositiveIntegerField(
        _('heures d\'annulation gratuite'),
        default=24,
        help_text=_('Nombre d\'heures avant la réservation pour annulation gratuite')
    )
    
    # Restrictions
    allowed_terrains = models.ManyToManyField(
        'terrains.Terrain',
        blank=True,
        related_name='memberships',
        verbose_name=_('terrains autorisés')
    )
    max_booking_days_in_advance = models.PositiveIntegerField(
        _('jours max de réservation à l\'avance'),
        null=True,
        blank=True
    )
    
    # Configuration
    is_active = models.BooleanField(_('actif'), default=True)
    is_public = models.BooleanField(_('public'), default=True)
    requires_approval = models.BooleanField(_('requiert validation'), default=False)
    
    # Limites
    max_subscribers = models.PositiveIntegerField(
        _('max abonnés'),
        null=True,
        blank=True,
        help_text=_('Nombre maximum d\'abonnés autorisés')
    )
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.base_price} {self.currency}/{self.recurrence_type}"

    @property
    def monthly_price(self):
        """Calcule le prix mensuel équivalent"""
        if self.recurrence_type == RecurrenceType.MONTHLY:
            return self.base_price
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            return self.base_price * Decimal('4.33')  # ~4.33 semaines par mois
        elif self.recurrence_type == RecurrenceType.YEARLY:
            return self.base_price / Decimal('12')
        elif self.recurrence_type == RecurrenceType.QUARTERLY:
            return self.base_price / Decimal('3')
        else:  # DAILY
            return self.base_price * Decimal('30')

    def can_user_subscribe(self, user: User) -> Tuple[bool, str]:
        """Vérifie si un utilisateur peut s'abonner"""
        if not self.is_active:
            return False, "Cet abonnement n'est pas actif"
        
        if not self.is_public and self.requires_approval:
            return False, "Cet abonnement nécessite une validation"
        
        if self.max_subscribers:
            current_count = Subscription.objects.filter(
                membership=self,
                status=SubscriptionStatus.ACTIVE
            ).count()
            if current_count >= self.max_subscribers:
                return False, "Le nombre maximum d'abonnés est atteint"
        
        return True, "Autorisé"


class Subscription(models.Model):
    """Abonnements des utilisateurs"""
    class Meta:
        verbose_name = _('abonnement')
        verbose_name_plural = _('abonnements')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['membership', 'status']),
            models.Index(fields=['end_date']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name=_('utilisateur')
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name=_('type d\'abonnement')
    )
    
    # Période
    start_date = models.DateTimeField(_('date de début'))
    end_date = models.DateTimeField(_('date de fin'))
    
    # Statut et paiement
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE
    )
    
    # Tarification
    price_paid = models.DecimalField(
        _('prix payé'),
        max_digits=10,
        decimal_places=2
    )
    currency = models.CharField(_('devise'), max_length=3, default='XOF')
    
    # Utilisation
    reservations_used_this_month = models.PositiveIntegerField(
        _('réservations utilisées ce mois'),
        default=0
    )
    hours_used_this_month = models.PositiveIntegerField(
        _('heures utilisées ce mois'),
        default=0
    )
    
    last_usage_reset = models.DateField(
        _('dernière réinitialisation usage'),
        default=date.today
    )
    
    # Auto-renouvellement
    auto_renew = models.BooleanField(_('auto-renouvellement'), default=True)
    
    # Validation
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_subscriptions',
        verbose_name=_('validé par')
    )
    approval_notes = models.TextField(
        _('notes de validation'),
        blank=True
    )
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.membership.name}"

    @property
    def is_active(self):
        """Vérifie si l'abonnement est actif"""
        return (
            self.status == SubscriptionStatus.ACTIVE and
            self.end_date > timezone.now()
        )

    @property
    def days_remaining(self):
        """Jours restants dans l'abonnement"""
        if not self.is_active:
            return 0
        return (self.end_date - timezone.now()).days

    @property
    def can_make_reservation(self) -> Tuple[bool, str]:
        """Vérifie si l'utilisateur peut faire une réservation"""
        if not self.is_active:
            return False, "Abonnement inactif"
        
        # Réinitialiser les compteurs mensuels si nécessaire
        self._reset_monthly_usage()
        
        membership = self.membership
        
        # Vérifier les limites de réservations
        if membership.max_reservations_per_month:
            if self.reservations_used_this_month >= membership.max_reservations_per_month:
                return False, f"Limite mensuelle atteinte ({membership.max_reservations_per_month} réservations)"
        
        if membership.max_reservations_per_week:
            # TODO: Implémenter la vérification hebdomadaire
            pass
        
        if membership.included_hours_per_month:
            if self.hours_used_this_month >= membership.included_hours_per_month:
                return False, f"Limite d'heures atteinte ({membership.included_hours_per_month} heures)"
        
        return True, "Autorisé"

    def _reset_monthly_usage(self):
        """Réinitialise les compteurs d'utilisation mensuels"""
        today = date.today()
        if self.last_usage_reset.month != today.month or self.last_usage_reset.year != today.year:
            self.reservations_used_this_month = 0
            self.hours_used_this_month = 0
            self.last_usage_reset = today
            self.save()

    def record_reservation_usage(self, duration_hours: Decimal):
        """Enregistre l'utilisation d'une réservation"""
        self._reset_monthly_usage()
        self.reservations_used_this_month += 1
        self.hours_used_this_month += int(duration_hours)
        self.save()

    def get_discount_for_reservation(self, base_price: Decimal) -> Decimal:
        """Calcule la réduction pour une réservation"""
        if not self.is_active:
            return Decimal('0')
        
        return base_price * (self.membership.discount_percentage / 100)


class CreditPackage(models.Model):
    """Forfaits de crédits prépayés"""
    class Meta:
        verbose_name = _('forfait de crédits')
        verbose_name_plural = _('forfaits de crédits')
        ordering = ['price']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nom'), max_length=100)
    description = models.TextField(_('description'))
    
    # Crédits
    credit_amount = models.PositiveIntegerField(
        _('nombre de crédits'),
        help_text=_('Nombre de crédits inclus dans le forfait')
    )
    credit_type = models.CharField(
        _('type de crédits'),
        max_length=20,
        choices=[
            ('hours', _('Heures')),
            ('reservations', _('Réservations')),
            ('minutes', _('Minutes')),
        ],
        default='hours'
    )
    
    # Tarification
    price = models.DecimalField(
        _('prix'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(_('devise'), max_length=3, default='XOF')
    
    # Bonus
    bonus_credits = models.PositiveIntegerField(
        _('crédits bonus'),
        default=0,
        help_text=_('Crédits supplémentaires offerts')
    )
    
    # Validité
    validity_days = models.PositiveIntegerField(
        _('validité en jours'),
        null=True,
        blank=True,
        help_text=_('Nombre de jours avant expiration des crédits')
    )
    
    # Configuration
    is_active = models.BooleanField(_('actif'), default=True)
    is_popular = models.BooleanField(_('populaire'), default=False)
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.credit_amount + self.bonus_credits} {self.credit_type}"

    @property
    def total_credits(self):
        """Total des crédits (bonus inclus)"""
        return self.credit_amount + self.bonus_credits

    @property
    def price_per_credit(self):
        """Prix par crédit"""
        if self.total_credits == 0:
            return Decimal('0')
        return self.price / Decimal(self.total_credits)


class UserCredit(models.Model):
    """Crédits des utilisateurs"""
    class Meta:
        verbose_name = _('crédit utilisateur')
        verbose_name_plural = _('crédits utilisateurs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'credit_type']),
            models.Index(fields=['expires_at']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credits',
        verbose_name=_('utilisateur')
    )
    credit_package = models.ForeignKey(
        CreditPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_credits',
        verbose_name=_('forfait d\'origine')
    )
    
    # Crédits
    amount = models.DecimalField(
        _('montant'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    credit_type = models.CharField(
        _('type de crédits'),
        max_length=20,
        choices=[
            ('hours', _('Heures')),
            ('reservations', _('Réservations')),
            ('minutes', _('Minutes')),
        ]
    )
    
    # Statut
    is_active = models.BooleanField(_('actif'), default=True)
    expires_at = models.DateTimeField(
        _('date d\'expiration'),
        null=True,
        blank=True
    )
    
    # Transaction
    transaction_id = models.CharField(
        _('ID transaction'),
        max_length=100,
        blank=True
    )
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.amount} {self.credit_type}"

    @property
    def is_expired(self):
        """Vérifie si les crédits sont expirés"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def is_available(self):
        """Vérifie si les crédits sont disponibles"""
        return self.is_active and not self.is_expired and self.amount > 0

    def use_credits(self, amount_to_use: Decimal) -> bool:
        """Utilise des crédits"""
        if not self.is_available or self.amount < amount_to_use:
            return False
        
        self.amount -= amount_to_use
        self.save()
        return True


class RecurringReservation(models.Model):
    """Réservations récurrentes"""
    class Meta:
        verbose_name = _('réservation récurrente')
        verbose_name_plural = _('réservations récurrentes')
        ordering = ['-created_at']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recurring_reservations',
        verbose_name=_('utilisateur')
    )
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='recurring_reservations',
        verbose_name=_('terrain')
    )
    
    # Pattern de récurrence
    recurrence_pattern = models.JSONField(
        _('pattern de récurrence'),
        help_text=_('Configuration de la récurrence (RRULE format)')
    )
    
    # Horaires
    start_time = models.TimeField(_('heure de début'))
    end_time = models.TimeField(_('heure de fin'))
    duration_minutes = models.PositiveIntegerField(_('durée en minutes'))
    
    # Période
    start_date = models.DateField(_('date de début'))
    end_date = models.DateField(_('date de fin'))
    
    # Statut
    is_active = models.BooleanField(_('actif'), default=True)
    
    # Réservations générées
    generated_reservations = models.ManyToManyField(
        'reservations.Reservation',
        blank=True,
        related_name='recurring_pattern',
        verbose_name=_('réservations générées')
    )
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.terrain.name} (Récurrent)"

    def generate_next_reservations(self, days_ahead: int = 30) -> List['Reservation']:
        """Génère les prochaines réservations selon le pattern"""
        # TODO: Implémenter la génération basée sur le pattern de récurrence
        # Pour l'instant, retourner une liste vide
        return []
