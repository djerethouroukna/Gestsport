# pricing/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime, date, time
import uuid

User = get_user_model()


class PricingPeriodType(models.TextChoices):
    HOURLY = 'hourly', _('Par heure')
    DAILY = 'daily', _('Par jour')
    WEEKLY = 'weekly', _('Par semaine')
    MONTHLY = 'monthly', _('Par mois')


class PricingRuleType(models.TextChoices):
    MULTIPLIER = 'multiplier', _('Multiplicateur')
    FIXED_AMOUNT = 'fixed_amount', _('Montant fixe')
    PERCENTAGE = 'percentage', _('Pourcentage')
    TIERED = 'tiered', _('Paliers')


class DayType(models.TextChoices):
    WEEKDAY = 'weekday', _('Jour de semaine')
    WEEKEND = 'weekend', _('Week-end')
    HOLIDAY = 'holiday', _('Jour férié')
    SPECIAL = 'special', _('Jour spécial')


class DynamicPricingRule(models.Model):
    """Règles de tarification dynamique avancées"""
    class Meta:
        verbose_name = _('règle de tarification dynamique')
        verbose_name_plural = _('règles de tarification dynamique')
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['terrain', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['priority']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='dynamic_pricing_rules',
        verbose_name=_('terrain')
    )
    name = models.CharField(_('nom'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    rule_type = models.CharField(
        _('type de règle'),
        max_length=20,
        choices=PricingRuleType.choices
    )
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
    
    # Types de jours
    day_types = models.JSONField(
        _('types de jours'),
        default=list,
        blank=True,
        help_text=_('Liste des types de jours concernés')
    )
    
    # Conditions de réservation
    min_duration_minutes = models.PositiveIntegerField(
        _('durée minimale (minutes)'),
        null=True,
        blank=True
    )
    max_duration_minutes = models.PositiveIntegerField(
        _('durée maximale (minutes)'),
        null=True,
        blank=True
    )
    min_advance_days = models.PositiveIntegerField(
        _('jours minimum à l\'avance'),
        null=True,
        blank=True
    )
    max_advance_days = models.PositiveIntegerField(
        _('jours maximum à l\'avance'),
        null=True,
        blank=True
    )
    
    # Valeurs de tarification
    multiplier_value = models.DecimalField(
        _('multiplicateur'),
        max_digits=5,
        decimal_places=3,
        default=Decimal('1.000'),
        help_text=_('Multiplicateur appliqué au prix de base')
    )
    fixed_amount = models.DecimalField(
        _('montant fixe'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Montant fixe à ajouter ou soustraire')
    )
    percentage_value = models.DecimalField(
        _('pourcentage'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Pourcentage d\'augmentation ou de réduction')
    )
    
    # Configuration des paliers
    tier_config = models.JSONField(
        _('configuration des paliers'),
        default=dict,
        blank=True,
        help_text=_('Configuration pour les tarifs par paliers')
    )
    
    # Limites et conditions
    max_applications_per_day = models.PositiveIntegerField(
        _('max applications par jour'),
        null=True,
        blank=True
    )
    max_applications_per_user = models.PositiveIntegerField(
        _('max applications par utilisateur'),
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.terrain.name} - {self.name}"

    def applies_to_datetime(self, target_datetime: datetime, user: User = None) -> bool:
        """Vérifie si la règle s'applique à un datetime donné"""
        # Vérifier les dates
        if self.start_date and target_datetime.date() < self.start_date:
            return False
        if self.end_date and target_datetime.date() > self.end_date:
            return False
        
        # Vérifier les heures
        if self.start_time and target_datetime.time() < self.start_time:
            return False
        if self.end_time and target_datetime.time() > self.end_time:
            return False
        
        # Vérifier les types de jours
        if self.day_types:
            day_type = self._get_day_type(target_datetime.date())
            if day_type not in self.day_types:
                return False
        
        return True
    
    def _get_day_type(self, target_date: date) -> str:
        """Détermine le type de jour pour une date"""
        # Vérifier si c'est un week-end
        if target_date.weekday() >= 5:  # Samedi (5) ou Dimanche (6)
            return DayType.WEEKEND
        
        # TODO: Implémenter la vérification des jours fériés
        # Pour l'instant, considérer tous les autres jours comme jours de semaine
        return DayType.WEEKDAY
    
    def calculate_price_adjustment(self, base_price: Decimal, duration_minutes: int) -> Decimal:
        """Calcule l'ajustement de prix selon la règle"""
        if self.rule_type == PricingRuleType.MULTIPLIER:
            return base_price * self.multiplier_value
        
        elif self.rule_type == PricingRuleType.FIXED_AMOUNT:
            return base_price + self.fixed_amount
        
        elif self.rule_type == PricingRuleType.PERCENTAGE:
            adjustment = base_price * (self.percentage_value / 100)
            return base_price + adjustment
        
        elif self.rule_type == PricingRuleType.TIERED:
            return self._calculate_tiered_price(base_price, duration_minutes)
        
        return base_price
    
    def _calculate_tiered_price(self, base_price: Decimal, duration_minutes: int) -> Decimal:
        """Calcule le prix par paliers"""
        if not self.tier_config:
            return base_price
        
        # Exemple de configuration de paliers:
        # {
        #   "tiers": [
        #     {"min_minutes": 0, "max_minutes": 60, "multiplier": 1.0},
        #     {"min_minutes": 61, "max_minutes": 120, "multiplier": 0.9},
        #     {"min_minutes": 121, "max_minutes": null, "multiplier": 0.8}
        #   ]
        # }
        
        tiers = self.tier_config.get('tiers', [])
        for tier in tiers:
            min_minutes = tier.get('min_minutes', 0)
            max_minutes = tier.get('max_minutes')
            
            if duration_minutes >= min_minutes:
                if max_minutes is None or duration_minutes <= max_minutes:
                    multiplier = Decimal(str(tier.get('multiplier', 1.0)))
                    return base_price * multiplier
        
        return base_price


class Holiday(models.Model):
    """Jours fériés et jours spéciaux"""
    class Meta:
        verbose_name = _('jour férié')
        verbose_name_plural = _('jours fériés')
        ordering = ['date']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('nom'), max_length=100)
    date = models.DateField(_('date'))
    day_type = models.CharField(
        _('type de jour'),
        max_length=20,
        choices=DayType.choices,
        default=DayType.HOLIDAY
    )
    is_recurring = models.BooleanField(_('récurrent'), default=False)
    description = models.TextField(_('description'), blank=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.date}"


class PriceHistory(models.Model):
    """Historique des prix appliqués"""
    class Meta:
        verbose_name = _('historique de prix')
        verbose_name_plural = _('historiques de prix')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['terrain', 'created_at']),
            models.Index(fields=['reservation']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name=_('terrain')
    )
    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        related_name='price_history',
        null=True,
        blank=True,
        verbose_name=_('réservation')
    )
    base_price = models.DecimalField(_('prix de base'), max_digits=10, decimal_places=2)
    final_price = models.DecimalField(_('prix final'), max_digits=10, decimal_places=2)
    applied_rules = models.JSONField(
        _('règles appliquées'),
        default=list,
        blank=True
    )
    price_adjustments = models.JSONField(
        _('ajustements de prix'),
        default=dict,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='price_history',
        verbose_name=_('utilisateur')
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)

    def __str__(self):
        return f"Prix {self.terrain.name} - {self.final_price}"

    @property
    def total_discount(self):
        """Calcule le montant total de la réduction"""
        return max(Decimal('0'), self.base_price - self.final_price)
    
    @property
    def discount_percentage(self):
        """Calcule le pourcentage de réduction"""
        if self.base_price == 0:
            return Decimal('0')
        return (self.total_discount / self.base_price) * 100


class PricingAnalytics(models.Model):
    """Analytics de tarification"""
    class Meta:
        verbose_name = _('analytique de tarification')
        verbose_name_plural = _('analytiques de tarification')
        ordering = ['-date']
        unique_together = ['terrain', 'date']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    terrain = models.ForeignKey(
        'terrains.Terrain',
        on_delete=models.CASCADE,
        related_name='pricing_analytics',
        verbose_name=_('terrain')
    )
    date = models.DateField(_('date'))
    
    # Statistiques de prix
    avg_price_per_hour = models.DecimalField(
        _('prix moyen par heure'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    min_price_per_hour = models.DecimalField(
        _('prix minimum par heure'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    max_price_per_hour = models.DecimalField(
        _('prix maximum par heure'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # Statistiques de réservations
    total_reservations = models.PositiveIntegerField(_('total réservations'), default=0)
    total_revenue = models.DecimalField(
        _('revenu total'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )
    
    # Utilisation des règles
    rules_applied_count = models.PositiveIntegerField(
        _('règles appliquées'),
        default=0
    )
    most_used_rule = models.CharField(
        _('règle la plus utilisée'),
        max_length=100,
        blank=True
    )
    
    # Taux d'occupation
    occupancy_rate = models.DecimalField(
        _('taux d\'occupation'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0')
    )
    
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Analytics {self.terrain.name} - {self.date}"
