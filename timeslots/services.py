# timeslots/services.py
from datetime import datetime, timedelta, date, time
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from typing import List, Dict, Optional, Tuple

from .models import TimeSlot, AvailabilityRule, TimeSlotGeneration, TimeSlotBlock, TimeSlotStatus
from terrains.models import Terrain, OpeningHours

User = get_user_model()


class TimeSlotService:
    """Service de gestion des créneaux horaires"""
    
    @staticmethod
    def generate_daily_timeslots(terrain: Terrain, target_date: date, duration_minutes: int = 60) -> List[TimeSlot]:
        """Génère les créneaux horaires pour un jour spécifique"""
        timeslots = []
        
        # Récupérer les heures d'ouverture pour ce jour
        opening_hours = terrain.opening_hours.filter(
            day_of_week=target_date.weekday(),
            is_closed=False
        ).first()
        
        if not opening_hours:
            return timeslots
        
        # Générer les créneaux
        current_time = datetime.combine(target_date, opening_hours.opening_time)
        end_time = datetime.combine(target_date, opening_hours.closing_time)
        
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_end_time = (current_time + timedelta(minutes=duration_minutes)).time()
            
            # Vérifier si le créneau existe déjà
            existing_slot = TimeSlot.objects.filter(
                terrain=terrain,
                date=target_date,
                start_time=current_time.time(),
                end_time=slot_end_time
            ).first()
            
            if not existing_slot:
                timeslot = TimeSlot(
                    terrain=terrain,
                    date=target_date,
                    start_time=current_time.time(),
                    end_time=slot_end_time,
                    status=TimeSlotStatus.AVAILABLE
                )
                timeslots.append(timeslot)
            
            current_time += timedelta(minutes=duration_minutes)
        
        return timeslots
    
    @staticmethod
    def generate_range_timeslots(
        terrain: Terrain, 
        start_date: date, 
        end_date: date, 
        duration_minutes: int = 60,
        created_by: Optional[User] = None
    ) -> Dict[str, int]:
        """Génère les créneaux horaires pour une période"""
        total_slots = 0
        current_date = start_date
        
        with transaction.atomic():
            while current_date <= end_date:
                daily_slots = TimeSlotService.generate_daily_timeslots(terrain, current_date, duration_minutes)
                
                # Créer les créneaux en base
                for slot in daily_slots:
                    slot.save()
                    total_slots += 1
                
                current_date += timedelta(days=1)
            
            # Enregistrer la génération
            TimeSlotGeneration.objects.create(
                terrain=terrain,
                start_date=start_date,
                end_date=end_date,
                slot_duration=duration_minutes,
                slots_generated=total_slots,
                generation_method='automatic',
                created_by=created_by
            )
        
        return {
            'terrain': terrain.name,
            'start_date': start_date,
            'end_date': end_date,
            'duration_minutes': duration_minutes,
            'slots_generated': total_slots
        }
    
    @staticmethod
    def get_available_timeslots(
        terrain: Terrain, 
        target_date: date, 
        start_time: Optional[time] = None,
        end_time: Optional[time] = None
    ) -> List[TimeSlot]:
        """Récupère les créneaux disponibles pour un terrain et une date"""
        queryset = TimeSlot.objects.filter(
            terrain=terrain,
            date=target_date,
            status=TimeSlotStatus.AVAILABLE
        )
        
        if start_time:
            queryset = queryset.filter(start_time__gte=start_time)
        if end_time:
            queryset = queryset.filter(end_time__lte=end_time)
        
        return list(queryset.order_by('start_time'))
    
    @staticmethod
    def check_availability(
        terrain: Terrain, 
        start_datetime: datetime, 
        end_datetime: datetime
    ) -> Tuple[bool, List[TimeSlot]]:
        """Vérifie la disponibilité pour une période donnée"""
        target_date = start_datetime.date()
        start_time = start_datetime.time()
        end_time = end_datetime.time()
        
        # Récupérer tous les créneaux qui chevauchent la période demandée
        overlapping_slots = TimeSlot.objects.filter(
            terrain=terrain,
            date=target_date,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(status=TimeSlotStatus.AVAILABLE)
        
        is_available = not overlapping_slots.exists()
        return is_available, list(overlapping_slots)
    
    @staticmethod
    def book_timeslot(timeslot: TimeSlot, reservation) -> bool:
        """Réserve un créneau horaire"""
        if not timeslot.can_be_booked:
            return False
        
        with transaction.atomic():
            timeslot.mark_as_booked(reservation)
            return True
    
    @staticmethod
    def release_timeslot(timeslot: TimeSlot) -> bool:
        """Libère un créneau horaire"""
        if timeslot.status != TimeSlotStatus.BOOKED:
            return False
        
        with transaction.atomic():
            timeslot.mark_as_available()
            return True
    
    @staticmethod
    def block_timeslots(
        terrain: Terrain,
        start_datetime: datetime,
        end_datetime: datetime,
        reason: str,
        created_by: User,
        is_maintenance: bool = False
    ) -> int:
        """Bloque des créneaux horaires"""
        target_date = start_datetime.date()
        start_time = start_datetime.time()
        end_time = end_datetime.time()
        
        # Créer le blocage
        block = TimeSlotBlock.objects.create(
            terrain=terrain,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            reason=reason,
            is_maintenance=is_maintenance,
            created_by=created_by
        )
        
        # Bloquer les créneaux concernés
        blocked_count = TimeSlot.objects.filter(
            terrain=terrain,
            date=target_date,
            start_time__gte=start_time,
            end_time__lte=end_time,
            status=TimeSlotStatus.AVAILABLE
        ).update(status=TimeSlotStatus.BLOCKED)
        
        return blocked_count
    
    @staticmethod
    def get_timeslot_price(timeslot: TimeSlot) -> Decimal:
        """Calcule le prix effectif d'un créneau"""
        base_price = timeslot.effective_price
        
        # Appliquer les règles de disponibilité
        rules = AvailabilityRule.objects.filter(
            terrain=timeslot.terrain,
            is_active=True
        ).order_by('-priority')
        
        for rule in rules:
            if rule.applies_to_date(timeslot.date) and rule.applies_to_time(timeslot.start_time):
                if rule.rule_type == 'price_override':
                    return rule.get_adjusted_price(base_price)
        
        return base_price
    
    @staticmethod
    def get_daily_availability(terrain: Terrain, target_date: date) -> Dict:
        """Récupère la disponibilité complète pour un jour"""
        timeslots = TimeSlot.objects.filter(
            terrain=terrain,
            date=target_date
        ).order_by('start_time')
        
        total_slots = timeslots.count()
        available_slots = timeslots.filter(status=TimeSlotStatus.AVAILABLE).count()
        booked_slots = timeslots.filter(status=TimeSlotStatus.BOOKED).count()
        blocked_slots = timeslots.filter(status=TimeSlotStatus.BLOCKED).count()
        
        return {
            'date': target_date,
            'terrain': terrain.name,
            'total_slots': total_slots,
            'available_slots': available_slots,
            'booked_slots': booked_slots,
            'blocked_slots': blocked_slots,
            'availability_rate': (available_slots / total_slots * 100) if total_slots > 0 else 0,
            'timeslots': [
                {
                    'id': str(slot.id),
                    'start_time': slot.start_time.strftime('%H:%M'),
                    'end_time': slot.end_time.strftime('%H:%M'),
                    'status': slot.status,
                    'price': float(TimeSlotService.get_timeslot_price(slot))
                }
                for slot in timeslots
            ]
        }
    
    @staticmethod
    def get_weekly_availability(terrain: Terrain, start_date: date) -> Dict:
        """Récupère la disponibilité pour une semaine"""
        weekly_data = {}
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            daily_data = TimeSlotService.get_daily_availability(terrain, current_date)
            weekly_data[current_date.strftime('%Y-%m-%d')] = daily_data
        
        return weekly_data
    
    @staticmethod
    def find_best_timeslot(
        terrain: Terrain, 
        target_date: date, 
        preferred_time: Optional[time] = None,
        duration_minutes: int = 60
    ) -> Optional[TimeSlot]:
        """Trouve le meilleur créneau disponible"""
        available_slots = TimeSlotService.get_available_timeslots(terrain, target_date)
        
        if not available_slots:
            return None
        
        if preferred_time:
            # Chercher le créneau le plus proche de l'heure préférée
            preferred_datetime = datetime.combine(target_date, preferred_time)
            
            best_slot = None
            min_diff = float('inf')
            
            for slot in available_slots:
                slot_datetime = datetime.combine(target_date, slot.start_time)
                diff = abs((slot_datetime - preferred_datetime).total_seconds())
                
                if diff < min_diff:
                    min_diff = diff
                    best_slot = slot
            
            return best_slot
        
        # Retourner le premier créneau disponible
        return available_slots[0]


class AvailabilityRuleService:
    """Service de gestion des règles de disponibilité"""
    
    @staticmethod
    def create_price_rule(
        terrain: Terrain,
        name: str,
        start_date: date,
        end_date: date,
        price_multiplier: Decimal,
        days_of_week: List[int] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        priority: int = 0
    ) -> AvailabilityRule:
        """Crée une règle de prix"""
        rule = AvailabilityRule.objects.create(
            terrain=terrain,
            rule_type='price_override',
            name=name,
            start_date=start_date,
            end_date=end_date,
            price_multiplier=price_multiplier,
            priority=priority,
            start_time=start_time,
            end_time=end_time
        )
        
        # Configurer les jours de la semaine
        if days_of_week:
            day_fields = [
                'monday', 'tuesday', 'wednesday', 'thursday',
                'friday', 'saturday', 'sunday'
            ]
            
            for i, day_field in enumerate(day_fields):
                if i in days_of_week:
                    setattr(rule, day_field, True)
            
            rule.save()
        
        return rule
    
    @staticmethod
    def create_weekend_premium_rule(terrain: Terrain, multiplier: Decimal = Decimal('1.5')) -> AvailabilityRule:
        """Crée une règle pour majorer les prix le week-end"""
        return AvailabilityRuleService.create_price_rule(
            terrain=terrain,
            name="Majoration week-end",
            start_date=date.today(),
            end_date=date.today().replace(year=date.today().year + 10),
            price_multiplier=multiplier,
            days_of_week=[5, 6],  # Samedi, Dimanche
            priority=10
        )
    
    @staticmethod
    def create_evening_premium_rule(
        terrain: Terrain, 
        start_time: time = time(18, 0),
        multiplier: Decimal = Decimal('1.3')
    ) -> AvailabilityRule:
        """Crée une règle pour majorer les prix en soirée"""
        return AvailabilityRule.objects.create(
            terrain=terrain,
            rule_type='price_override',
            name="Majoration soirée",
            start_date=date.today(),
            end_date=date.today().replace(year=date.today().year + 10),
            start_time=start_time,
            price_multiplier=multiplier,
            priority=5
        )
    
    @staticmethod
    def get_applicable_rules(terrain: Terrain, target_date: date, target_time: time) -> List[AvailabilityRule]:
        """Récupère les règles applicables pour une date et heure"""
        return AvailabilityRule.objects.filter(
            terrain=terrain,
            is_active=True
        ).filter(
            models.Q(start_date__lte=target_date) | models.Q(start_date__isnull=True),
            models.Q(end_date__gte=target_date) | models.Q(end_date__isnull=True)
        ).order_by('-priority')


class TimeSlotBulkService:
    """Service pour les opérations massives sur les créneaux"""
    
    @staticmethod
    def regenerate_month_timeslots(terrain: Terrain, year: int, month: int, created_by: User) -> Dict:
        """Régénère tous les créneaux pour un mois"""
        start_date = date(year, month, 1)
        
        # Calculer la fin du mois
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Supprimer les créneaux existants
        deleted_count = TimeSlot.objects.filter(
            terrain=terrain,
            date__gte=start_date,
            date__lte=end_date
        ).delete()[0]
        
        # Générer les nouveaux créneaux
        result = TimeSlotService.generate_range_timeslots(
            terrain=terrain,
            start_date=start_date,
            end_date=end_date,
            duration_minutes=60,
            created_by=created_by
        )
        
        result['deleted_slots'] = deleted_count
        result['net_change'] = result['slots_generated'] - deleted_count
        
        return result
    
    @staticmethod
    def cleanup_old_timeslots(days_to_keep: int = 90) -> int:
        """Nettoie les anciens créneaux"""
        cutoff_date = timezone.now().date() - timedelta(days=days_to_keep)
        
        deleted_count = TimeSlot.objects.filter(
            date__lt=cutoff_date,
            status=TimeSlotStatus.AVAILABLE
        ).delete()[0]
        
        return deleted_count
