# reservations/analytics.py - Tableaux de bord analytics unifiés
from django.db.models import Count, Sum, Avg, Q, F, DecimalField, Case, When
from django.db.models.functions import Coalesce, TruncDate, TruncMonth, Extract
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

from .models import Reservation, ReservationStatus
from terrains.models import Terrain
from payments.models import Payment, PaymentStatus
from pricing.models import PricingAnalytics, PriceHistory
from subscriptions.models import Subscription, UserCredit
from waitinglist.models import WaitingList, WaitingListStatistics


class ReservationAnalyticsService:
    """Service pour les analytics unifiés des réservations"""
    
    @staticmethod
    def get_dashboard_summary(start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        Tableau de bord principal avec statistiques unifiées
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        # Statistiques générales des réservations
        reservation_stats = Reservation.objects.filter(
            created_at__range=[start_date, end_date]
        ).aggregate(
            total_reservations=Count('id'),
            pending_reservations=Count('id', filter=Q(status=ReservationStatus.PENDING)),
            confirmed_reservations=Count('id', filter=Q(status=ReservationStatus.CONFIRMED)),
            completed_reservations=Count('id', filter=Q(status=ReservationStatus.COMPLETED)),
            cancelled_reservations=Count('id', filter=Q(status=ReservationStatus.CANCELLED)),
            avg_reservation_duration=Avg(
                F('end_time') - F('start_time')
            )
        )
        
        # Statistiques de paiement
        payment_stats = Payment.objects.filter(
            created_at__range=[start_date, end_date],
            status=PaymentStatus.COMPLETED
        ).aggregate(
            total_revenue=Sum('amount'),
            total_transactions=Count('id'),
            avg_transaction_amount=Avg('amount')
        )
        
        # Statistiques par terrain
        terrain_stats = Reservation.objects.filter(
            created_at__range=[start_date, end_date]
        ).values('terrain__name').annotate(
            reservations_count=Count('id'),
            revenue=Sum(
                Case(
                    When(payment__status=PaymentStatus.COMPLETED, then=F('payment__amount')),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            ),
            occupancy_rate=Avg(
                Case(
                    When(status=ReservationStatus.COMPLETED, then=1),
                    default=0,
                    output_field=DecimalField()
                )
            )
        ).order_by('-revenue')
        
        # Tendances journalières
        daily_trends = Reservation.objects.filter(
            created_at__range=[start_date, end_date]
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            reservations_count=Count('id'),
            revenue=Sum(
                Case(
                    When(payment__status=PaymentStatus.COMPLETED, then=F('payment__amount')),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            )
        ).order_by('date')
        
        # Statistiques des abonnements
        subscription_stats = Subscription.objects.filter(
            created_at__range=[start_date, end_date]
        ).aggregate(
            new_subscriptions=Count('id'),
            active_subscriptions=Count('id', filter=Q(status='active')),
            subscription_revenue=Sum('price_paid')
        )
        
        # Statistiques de la liste d'attente
        waiting_list_stats = WaitingList.objects.filter(
            created_at__range=[start_date, end_date]
        ).aggregate(
            total_waiting_entries=Count('id'),
            resolved_entries=Count('id', filter=Q(status__in=['accepted', 'cancelled'])),
            avg_waiting_time=Avg(
                Extract('updated_at', 'epoch') - Extract('created_at', 'epoch')
            )
        )
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "reservations": reservation_stats,
            "payments": payment_stats,
            "terrain_performance": list(terrain_stats),
            "daily_trends": list(daily_trends),
            "subscriptions": subscription_stats,
            "waiting_list": waiting_list_stats
        }
    
    @staticmethod
    def get_terrain_analytics(terrain_id: int, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        Analytics détaillés pour un terrain spécifique
        """
        try:
            terrain = Terrain.objects.get(id=terrain_id)
        except Terrain.DoesNotExist:
            return {"error": "Terrain non trouvé"}
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        # Statistiques de réservation pour ce terrain
        reservation_stats = Reservation.objects.filter(
            terrain=terrain,
            created_at__range=[start_date, end_date]
        ).aggregate(
            total_reservations=Count('id'),
            completed_reservations=Count('id', filter=Q(status=ReservationStatus.COMPLETED)),
            cancelled_reservations=Count('id', filter=Q(status=ReservationStatus.CANCELLED)),
            total_revenue=Sum(
                Case(
                    When(payment__status=PaymentStatus.COMPLETED, then=F('payment__amount')),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            ),
            avg_price_per_hour=Avg(
                Case(
                    When(payment__status=PaymentStatus.COMPLETED, then=F('payment__amount')),
                    default=Decimal('0'),
                    output_field=DecimalField()
                ) / Extract(F('end_time') - F('start_time'), 'epoch') * 3600
            )
        )
        
        # Taux d'occupation par heure
        hourly_occupancy = Reservation.objects.filter(
            terrain=terrain,
            start_time__range=[start_date, end_date]
        ).annotate(
            hour=Extract('start_time', 'hour')
        ).values('hour').annotate(
            reservations_count=Count('id')
        ).order_by('hour')
        
        # Performance des règles de tarification
        pricing_performance = PriceHistory.objects.filter(
            terrain=terrain,
            created_at__range=[start_date, end_date]
        ).aggregate(
            avg_base_price=Avg('base_price'),
            avg_final_price=Avg('final_price'),
            avg_discount=Avg(F('base_price') - F('final_price')),
            rules_usage_count=Count('applied_rules')
        )
        
        # Utilisation des abonnements pour ce terrain
        subscription_usage = Reservation.objects.filter(
            terrain=terrain,
            created_at__range=[start_date, end_date],
            user__subscriptions__status='active'
        ).distinct().count()
        
        return {
            "terrain": {
                "id": terrain.id,
                "name": terrain.name,
                "type": terrain.terrain_type,
                "capacity": terrain.capacity,
                "base_price": float(terrain.price_per_hour)
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "reservations": reservation_stats,
            "hourly_occupancy": list(hourly_occupancy),
            "pricing_performance": pricing_performance,
            "subscription_usage": subscription_usage
        }
    
    @staticmethod
    def get_user_analytics(user_id: int, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        Analytics pour un utilisateur spécifique
        """
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {"error": "Utilisateur non trouvé"}
        
        if not start_date:
            start_date = timezone.now() - timedelta(days=90)
        if not end_date:
            end_date = timezone.now()
        
        # Statistiques de réservation
        reservation_stats = Reservation.objects.filter(
            user=user,
            created_at__range=[start_date, end_date]
        ).aggregate(
            total_reservations=Count('id'),
            completed_reservations=Count('id', filter=Q(status=ReservationStatus.COMPLETED)),
            cancelled_reservations=Count('id', filter=Q(status=ReservationStatus.CANCELLED)),
            total_spent=Sum(
                Case(
                    When(payment__status=PaymentStatus.COMPLETED, then=F('payment__amount')),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            ),
            avg_reservation_cost=Avg(
                Case(
                    When(payment__status=PaymentStatus.COMPLETED, then=F('payment__amount')),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            )
        )
        
        # Terrains préférés
        preferred_terrains = Reservation.objects.filter(
            user=user,
            created_at__range=[start_date, end_date]
        ).values('terrain__name').annotate(
            reservation_count=Count('id')
        ).order_by('-reservation_count')[:5]
        
        # Abonnement actif
        active_subscription = Subscription.objects.filter(
            user=user,
            status='active',
            end_date__gt=timezone.now()
        ).select_related('membership').first()
        
        # Crédits disponibles
        available_credits = UserCredit.objects.filter(
            user=user,
            is_active=True,
            amount__gt=0
        ).aggregate(
            total_credits=Sum('amount'),
            credit_types=Count('credit_type', distinct=True)
        )
        
        # Historique de la liste d'attente
        waiting_list_history = WaitingList.objects.filter(
            user=user,
            created_at__range=[start_date, end_date]
        ).aggregate(
            total_waiting_entries=Count('id'),
            successful_conversions=Count('id', filter=Q(status='accepted')),
            avg_waiting_time=Avg(
                Extract('updated_at', 'epoch') - Extract('created_at', 'epoch')
            )
        )
        
        return {
            "user": {
                "id": user.id,
                "name": user.get_full_name(),
                "email": user.email,
                "role": user.role
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "reservations": reservation_stats,
            "preferred_terrains": list(preferred_terrains),
            "subscription": {
                "active": active_subscription is not None,
                "details": {
                    "name": active_subscription.membership.name,
                    "end_date": active_subscription.end_date.isoformat(),
                    "reservations_used": active_subscription.reservations_used_this_month,
                    "hours_used": active_subscription.hours_used_this_month
                } if active_subscription else None
            },
            "credits": available_credits,
            "waiting_list": waiting_list_history
        }
    
    @staticmethod
    def get_revenue_analytics(start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        Analytics détaillés des revenus
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=90)
        if not end_date:
            end_date = timezone.now()
        
        # Revenus par période
        monthly_revenue = Payment.objects.filter(
            status=PaymentStatus.COMPLETED,
            created_at__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('amount'),
            transaction_count=Count('id'),
            avg_transaction=Avg('amount')
        ).order_by('month')
        
        # Revenus par source
        revenue_by_source = Payment.objects.filter(
            status=PaymentStatus.COMPLETED,
            created_at__range=[start_date, end_date]
        ).values('payment_method__method_type').annotate(
            revenue=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-revenue')
        
        # Revenus par type de tarif
        pricing_revenue = PriceHistory.objects.filter(
            created_at__range=[start_date, end_date]
        ).values('terrain__name').annotate(
            base_revenue=Sum('base_price'),
            final_revenue=Sum('final_price'),
            total_discount=Sum(F('base_price') - F('final_price')),
            reservation_count=Count('id')
        ).order_by('-final_revenue')
        
        # Revenus des abonnements
        subscription_revenue = Subscription.objects.filter(
            created_at__range=[start_date, end_date]
        ).aggregate(
            new_subscription_revenue=Sum('price_paid'),
            new_subscriptions=Count('id')
        )
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "monthly_trends": list(monthly_revenue),
            "revenue_by_source": list(revenue_by_source),
            "pricing_performance": list(pricing_revenue),
            "subscription_revenue": subscription_revenue
        }
    
    @staticmethod
    def get_occupancy_analytics(start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        Analytics des taux d'occupation
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        # Occupation par terrain
        terrain_occupancy = []
        for terrain in Terrain.objects.all():
            total_possible_hours = 24 * (end_date - start_date).days
            reserved_hours = Reservation.objects.filter(
                terrain=terrain,
                start_time__range=[start_date, end_date],
                status=ReservationStatus.COMPLETED
            ).aggregate(
                total_hours=Sum(
                    Extract(F('end_time') - F('start_time'), 'epoch') / 3600
                )
            )['total_hours'] or 0
            
            occupancy_rate = (reserved_hours / total_possible_hours * 100) if total_possible_hours > 0 else 0
            
            terrain_occupancy.append({
                "terrain_name": terrain.name,
                "terrain_type": terrain.terrain_type,
                "total_possible_hours": total_possible_hours,
                "reserved_hours": reserved_hours,
                "occupancy_rate": round(occupancy_rate, 2)
            })
        
        # Occupation par jour de la semaine
        daily_occupancy = Reservation.objects.filter(
            start_time__range=[start_date, end_date],
            status=ReservationStatus.COMPLETED
        ).annotate(
            day_of_week=Extract('start_time', 'dow')
        ).values('day_of_week').annotate(
            reservation_count=Count('id')
        ).order_by('day_of_week')
        
        # Occupation par heure
        hourly_occupancy = Reservation.objects.filter(
            start_time__range=[start_date, end_date],
            status=ReservationStatus.COMPLETED
        ).annotate(
            hour=Extract('start_time', 'hour')
        ).values('hour').annotate(
            reservation_count=Count('id')
        ).order_by('hour')
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "terrain_occupancy": terrain_occupancy,
            "daily_patterns": list(daily_occupancy),
            "hourly_patterns": list(hourly_occupancy)
        }
