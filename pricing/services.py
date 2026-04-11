# pricing/services.py
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from django.utils import timezone
from django.db import transaction, models
from django.contrib.auth import get_user_model
from typing import List, Dict, Optional, Tuple

from .models import DynamicPricingRule, Holiday, PriceHistory, PricingAnalytics, DayType
from terrains.models import Terrain

User = get_user_model()


class DynamicPricingService:
    """Service principal de tarification dynamique"""
    
    @staticmethod
    def calculate_price(
        terrain: Terrain,
        start_datetime: datetime,
        end_datetime: datetime,
        user: User = None,
        base_price: Optional[Decimal] = None
    ) -> Dict:
        """
        Calcule le prix dynamique pour une réservation
        
        Returns:
            {
                'base_price': Decimal,
                'final_price': Decimal,
                'applied_rules': List[Dict],
                'price_adjustments': Dict,
                'total_discount': Decimal,
                'discount_percentage': Decimal
            }
        """
        # Calculer le prix de base
        if base_price is None:
            base_price = DynamicPricingService._calculate_base_price(terrain, start_datetime, end_datetime)
        
        # Récupérer les règles applicables
        applicable_rules = DynamicPricingService._get_applicable_rules(
            terrain, start_datetime, end_datetime, user
        )
        
        # Appliquer les règles dans l'ordre de priorité
        final_price = base_price
        applied_rules = []
        price_adjustments = {}
        
        for rule in applicable_rules:
            rule_result = DynamicPricingService._apply_rule(
                rule, final_price, start_datetime, end_datetime
            )
            
            if rule_result['applied']:
                final_price = rule_result['new_price']
                applied_rules.append({
                    'rule_id': str(rule.id),
                    'rule_name': rule.name,
                    'rule_type': rule.rule_type,
                    'adjustment': rule_result['adjustment']
                })
                price_adjustments[str(rule.id)] = rule_result['adjustment']
        
        # Calculer les statistiques
        total_discount = max(Decimal('0'), base_price - final_price)
        discount_percentage = (total_discount / base_price * 100) if base_price > 0 else Decimal('0')
        
        return {
            'base_price': base_price,
            'final_price': final_price,
            'applied_rules': applied_rules,
            'price_adjustments': price_adjustments,
            'total_discount': total_discount,
            'discount_percentage': discount_percentage
        }
    
    @staticmethod
    def _calculate_base_price(terrain: Terrain, start_datetime: datetime, end_datetime: datetime) -> Decimal:
        """Calcule le prix de base"""
        duration_hours = Decimal(str((end_datetime - start_datetime).total_seconds() / 3600))
        return terrain.price_per_hour * duration_hours
    
    @staticmethod
    def _get_applicable_rules(
        terrain: Terrain,
        start_datetime: datetime,
        end_datetime: datetime,
        user: User = None
    ) -> List[DynamicPricingRule]:
        """Récupère les règles applicables triées par priorité"""
        rules = DynamicPricingRule.objects.filter(
            terrain=terrain,
            is_active=True
        ).order_by('-priority')
        
        applicable_rules = []
        
        for rule in rules:
            # Vérifier si la règle s'applique à la période
            if not rule.applies_to_datetime(start_datetime, user):
                continue
            
            # Vérifier les conditions de durée
            duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
            
            if rule.min_duration_minutes and duration_minutes < rule.min_duration_minutes:
                continue
            
            if rule.max_duration_minutes and duration_minutes > rule.max_duration_minutes:
                continue
            
            # Vérifier les conditions d'avance
            days_in_advance = (start_datetime.date() - timezone.now().date()).days
            
            if rule.min_advance_days and days_in_advance < rule.min_advance_days:
                continue
            
            if rule.max_advance_days and days_in_advance > rule.max_advance_days:
                continue
            
            # TODO: Vérifier les limites d'utilisation
            # Pour l'instant, on ignore cette vérification
            
            applicable_rules.append(rule)
        
        return applicable_rules
    
    @staticmethod
    def _apply_rule(
        rule: DynamicPricingRule,
        current_price: Decimal,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> Dict:
        """Applique une règle de tarification"""
        duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        new_price = rule.calculate_price_adjustment(current_price, duration_minutes)
        
        adjustment = {
            'type': rule.rule_type,
            'old_price': current_price,
            'new_price': new_price,
            'difference': new_price - current_price,
            'applied': new_price != current_price
        }
        
        if rule.rule_type == 'multiplier':
            adjustment['multiplier'] = rule.multiplier_value
        elif rule.rule_type == 'fixed_amount':
            adjustment['fixed_amount'] = rule.fixed_amount
        elif rule.rule_type == 'percentage':
            adjustment['percentage'] = rule.percentage_value
        
        return {
            'applied': new_price != current_price,
            'new_price': new_price,
            'adjustment': adjustment
        }
    
    @staticmethod
    def save_price_history(
        terrain: Terrain,
        base_price: Decimal,
        final_price: Decimal,
        applied_rules: List[Dict],
        price_adjustments: Dict,
        user: User = None,
        reservation=None
    ) -> PriceHistory:
        """Sauvegarde l'historique des prix"""
        return PriceHistory.objects.create(
            terrain=terrain,
            reservation=reservation,
            base_price=base_price,
            final_price=final_price,
            applied_rules=applied_rules,
            price_adjustments=price_adjustments,
            user=user
        )
    
    @staticmethod
    def get_price_trends(
        terrain: Terrain,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Récupère les tendances de prix pour une période"""
        price_history = PriceHistory.objects.filter(
            terrain=terrain,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        if not price_history.exists():
            return {
                'terrain': terrain.name,
                'period': f"{start_date} to {end_date}",
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'total_reservations': 0,
                'total_revenue': 0,
                'daily_prices': []
            }
        
        # Calculer les statistiques
        avg_price = price_history.aggregate(
            avg_price=models.Avg('final_price')
        )['avg_price'] or Decimal('0')
        
        min_price = price_history.aggregate(
            min_price=models.Min('final_price')
        )['min_price'] or Decimal('0')
        
        max_price = price_history.aggregate(
            max_price=models.Max('final_price')
        )['max_price'] or Decimal('0')
        
        total_revenue = price_history.aggregate(
            total_revenue=models.Sum('final_price')
        )['total_revenue'] or Decimal('0')
        
        # Prix quotidiens
        daily_prices = []
        current_date = start_date
        
        while current_date <= end_date:
            day_prices = price_history.filter(created_at__date=current_date)
            
            if day_prices.exists():
                day_avg = day_prices.aggregate(
                    avg_price=models.Avg('final_price')
                )['avg_price'] or Decimal('0')
                
                daily_prices.append({
                    'date': current_date.isoformat(),
                    'avg_price': float(day_avg),
                    'reservations': day_prices.count()
                })
            else:
                daily_prices.append({
                    'date': current_date.isoformat(),
                    'avg_price': 0,
                    'reservations': 0
                })
            
            current_date += timedelta(days=1)
        
        return {
            'terrain': terrain.name,
            'period': f"{start_date} to {end_date}",
            'avg_price': float(avg_price),
            'min_price': float(min_price),
            'max_price': float(max_price),
            'total_reservations': price_history.count(),
            'total_revenue': float(total_revenue),
            'daily_prices': daily_prices
        }


class PricingRuleService:
    """Service de gestion des règles de tarification"""
    
    @staticmethod
    def create_weekend_premium_rule(
        terrain: Terrain,
        multiplier: Decimal = Decimal('1.5'),
        priority: int = 10
    ) -> DynamicPricingRule:
        """Crée une règle de majoration week-end"""
        return DynamicPricingRule.objects.create(
            terrain=terrain,
            name="Majoration week-end",
            description="Majoration automatique les week-ends",
            rule_type='multiplier',
            priority=priority,
            day_types=[DayType.WEEKEND],
            multiplier_value=multiplier
        )
    
    @staticmethod
    def create_evening_premium_rule(
        terrain: Terrain,
        start_time: time = time(18, 0),
        end_time: time = time(22, 0),
        multiplier: Decimal = Decimal('1.3'),
        priority: int = 5
    ) -> DynamicPricingRule:
        """Crée une règle de majoration soirée"""
        return DynamicPricingRule.objects.create(
            terrain=terrain,
            name="Majoration soirée",
            description="Majoration automatique en soirée (18h-22h)",
            rule_type='multiplier',
            priority=priority,
            start_time=start_time,
            end_time=end_time,
            multiplier_value=multiplier
        )
    
    @staticmethod
    def create_early_bird_discount_rule(
        terrain: Terrain,
        min_advance_days: int = 7,
        discount_percentage: Decimal = Decimal('10'),
        priority: int = 15
    ) -> DynamicPricingRule:
        """Crée une règle de réduction early bird"""
        return DynamicPricingRule.objects.create(
            terrain=terrain,
            name="Réduction Early Bird",
            description=f"Réduction de {discount_percentage}% pour réservations > {min_advance_days} jours",
            rule_type='percentage',
            priority=priority,
            min_advance_days=min_advance_days,
            percentage_value=-discount_percentage  # Négatif pour une réduction
        )
    
    @staticmethod
    def create_last_minute_discount_rule(
        terrain: Terrain,
        max_advance_days: int = 1,
        discount_percentage: Decimal = Decimal('20'),
        priority: int = 20
    ) -> DynamicPricingRule:
        """Crée une règle de réduction last minute"""
        return DynamicPricingRule.objects.create(
            terrain=terrain,
            name="Réduction Last Minute",
            description=f"Réduction de {discount_percentage}% pour réservations < {max_advance_days} jours",
            rule_type='percentage',
            priority=priority,
            max_advance_days=max_advance_days,
            percentage_value=-discount_percentage  # Négatif pour une réduction
        )
    
    @staticmethod
    def create_tiered_pricing_rule(
        terrain: Terrain,
        tier_config: Dict,
        priority: int = 1
    ) -> DynamicPricingRule:
        """Crée une règle de tarification par paliers"""
        return DynamicPricingRule.objects.create(
            terrain=terrain,
            name="Tarification par paliers",
            description="Réduction progressive selon la durée",
            rule_type='tiered',
            priority=priority,
            tier_config=tier_config
        )
    
    @staticmethod
    def create_holiday_premium_rule(
        terrain: Terrain,
        multiplier: Decimal = Decimal('2.0'),
        priority: int = 25
    ) -> DynamicPricingRule:
        """Crée une règle de majoration jours fériés"""
        return DynamicPricingRule.objects.create(
            terrain=terrain,
            name="Majoration jours fériés",
            description="Majoration automatique les jours fériés",
            rule_type='multiplier',
            priority=priority,
            day_types=[DayType.HOLIDAY],
            multiplier_value=multiplier
        )


class HolidayService:
    """Service de gestion des jours fériés"""
    
    @staticmethod
    def create_holiday(
        name: str,
        date: date,
        day_type: str = DayType.HOLIDAY,
        is_recurring: bool = False,
        description: str = ""
    ) -> Holiday:
        """Crée un jour férié"""
        return Holiday.objects.create(
            name=name,
            date=date,
            day_type=day_type,
            is_recurring=is_recurring,
            description=description
        )
    
    @staticmethod
    def get_holidays_in_range(start_date: date, end_date: date) -> List[Holiday]:
        """Récupère les jours fériés dans une période"""
        return Holiday.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
    
    @staticmethod
    def is_holiday(target_date: date) -> bool:
        """Vérifie si une date est un jour férié"""
        return Holiday.objects.filter(date=target_date).exists()
    
    @staticmethod
    def get_upcoming_holidays(days_ahead: int = 30) -> List[Holiday]:
        """Récupère les jours fériés à venir"""
        end_date = timezone.now().date() + timedelta(days=days_ahead)
        return Holiday.objects.filter(
            date__gte=timezone.now().date(),
            date__lte=end_date
        ).order_by('date')


class PricingAnalyticsService:
    """Service d'analytics de tarification"""
    
    @staticmethod
    def update_daily_analytics(target_date: date = None):
        """Met à jour les analytics quotidiens"""
        if target_date is None:
            target_date = timezone.now().date()
        
        for terrain in Terrain.objects.all():
            # Calculer les statistiques pour le terrain et la date
            price_history = PriceHistory.objects.filter(
                terrain=terrain,
                created_at__date=target_date
            )
            
            if not price_history.exists():
                continue
            
            # Calculer les statistiques
            analytics_data = {
                'avg_price_per_hour': price_history.aggregate(
                    avg_price=models.Avg('final_price')
                )['avg_price'] or Decimal('0'),
                'min_price_per_hour': price_history.aggregate(
                    min_price=models.Min('final_price')
                )['min_price'] or Decimal('0'),
                'max_price_per_hour': price_history.aggregate(
                    max_price=models.Max('final_price')
                )['max_price'] or Decimal('0'),
                'total_reservations': price_history.count(),
                'total_revenue': price_history.aggregate(
                    total_revenue=models.Sum('final_price')
                )['total_revenue'] or Decimal('0'),
            }
            
            # Calculer le taux d'occupation
            from timeslots.models import TimeSlot
            total_slots = TimeSlot.objects.filter(
                terrain=terrain,
                date=target_date
            ).count()
            
            booked_slots = TimeSlot.objects.filter(
                terrain=terrain,
                date=target_date,
                status='booked'
            ).count()
            
            if total_slots > 0:
                analytics_data['occupancy_rate'] = Decimal(str(booked_slots / total_slots * 100))
            else:
                analytics_data['occupancy_rate'] = Decimal('0')
            
            # Mettre à jour ou créer l'analytics
            analytics, created = PricingAnalytics.objects.update_or_create(
                terrain=terrain,
                date=target_date,
                defaults=analytics_data
            )
    
    @staticmethod
    def get_revenue_summary(
        terrain: Terrain = None,
        start_date: date = None,
        end_date: date = None
    ) -> Dict:
        """Récupère un résumé des revenus"""
        if start_date is None:
            start_date = timezone.now().date() - timedelta(days=30)
        if end_date is None:
            end_date = timezone.now().date()
        
        queryset = PriceHistory.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        if terrain:
            queryset = queryset.filter(terrain=terrain)
        
        # Calculer les statistiques
        summary = queryset.aggregate(
            total_revenue=models.Sum('final_price'),
            total_reservations=models.Count('id'),
            avg_price=models.Avg('final_price'),
            total_discount=models.Sum(
                models.F('base_price') - models.F('final_price')
            )
        )
        
        return {
            'period': f"{start_date} to {end_date}",
            'terrain': terrain.name if terrain else 'All terrains',
            'total_revenue': float(summary['total_revenue'] or 0),
            'total_reservations': summary['total_reservations'] or 0,
            'avg_price': float(summary['avg_price'] or 0),
            'total_discount': float(summary['total_discount'] or 0)
        }
