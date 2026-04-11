from django.utils import timezone
from django.db.models import Q
from .models import Terrain
from reservations.models import Reservation

class TerrainAvailabilityService:
    """Service pour gérer la disponibilité des terrains"""
    
    @staticmethod
    def is_available_now(terrain):
        """Vérifie si un terrain est disponible maintenant"""
        if not terrain.is_available:
            return False
        
        now = timezone.now()
        
        # Vérifier les réservations en cours
        current_reservations = Reservation.objects.filter(
            terrain=terrain,
            status__in=['pending', 'confirmed'],
            start_time__lte=now,
            end_time__gt=now
        )
        
        return not current_reservations.exists()
    
    @staticmethod
    def get_availability_status(terrain):
        """Retourne le statut détaillé de disponibilité"""
        if not terrain.is_available:
            return {
                'status': 'unavailable',
                'message': 'Terrain indisponible',
                'available_at': None
            }
        
        now = timezone.now()
        
        # Vérifier réservation en cours
        current_reservations = Reservation.objects.filter(
            terrain=terrain,
            status__in=['pending', 'confirmed'],
            start_time__lte=now,
            end_time__gt=now
        )
        
        if current_reservations.exists():
            reservation = current_reservations.first()
            return {
                'status': 'occupied',
                'message': 'Terrain actuellement occupé',
                'available_at': reservation.end_time,
                'current_reservation': {
                    'id': reservation.id,
                    'user_name': reservation.user.get_full_name(),
                    'end_time': reservation.end_time
                }
            }
        
        # Prochaine réservation
        next_reservation = Reservation.objects.filter(
            terrain=terrain,
            status__in=['pending', 'confirmed'],
            start_time__gt=now
        ).order_by('start_time').first()
        
        if next_reservation:
            return {
                'status': 'available',
                'message': 'Disponible maintenant',
                'next_reservation': next_reservation.start_time,
                'next_reservation_details': {
                    'id': next_reservation.id,
                    'user_name': next_reservation.user.get_full_name(),
                    'start_time': next_reservation.start_time,
                    'end_time': next_reservation.end_time
                }
            }
        
        return {
            'status': 'fully_available',
            'message': 'Aucune réservation prévue',
            'available_at': None
        }
    
    @staticmethod
    def check_period_availability(terrain, start_time, end_time):
        """Vérifie la disponibilité pour une période spécifique"""
        if not terrain.is_available:
            return {
                'available': False,
                'reason': 'Terrain indisponible',
                'conflicts': []
            }
        
        # Vérifier les conflits de réservation
        conflicting_reservations = Reservation.objects.filter(
            terrain=terrain,
            status__in=['pending', 'confirmed'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if conflicting_reservations.exists():
            conflicts = []
            for reservation in conflicting_reservations:
                conflicts.append({
                    'id': reservation.id,
                    'user_name': reservation.user.get_full_name(),
                    'start_time': reservation.start_time,
                    'end_time': reservation.end_time,
                    'status': reservation.status
                })
            
            return {
                'available': False,
                'reason': 'Conflit de réservation',
                'conflicts': conflicts
            }
        
        return {
            'available': True,
            'reason': 'Disponible',
            'conflicts': []
        }
    
    @staticmethod
    def get_available_slots(terrain, date, duration_minutes=60):
        """Retourne les créneaux disponibles pour une date donnée"""
        if not terrain.is_available:
            return []
        
        # Définir les heures d'ouverture (9h-22h par défaut)
        from datetime import datetime, timedelta
        date_start = timezone.make_aware(
            datetime.combine(date, datetime.min.time()).replace(hour=9)
        )
        date_end = timezone.make_aware(
            datetime.combine(date, datetime.min.time()).replace(hour=22)
        )
        
        # Récupérer toutes les réservations pour cette date
        reservations = Reservation.objects.filter(
            terrain=terrain,
            status__in=['pending', 'confirmed'],
            start_time__date=date.date(),
            end_time__date=date.date()
        ).order_by('start_time')
        
        available_slots = []
        current_time = date_start
        slot_duration = timedelta(minutes=duration_minutes)
        
        while current_time + slot_duration <= date_end:
            slot_end = current_time + slot_duration
            
            # Vérifier si ce créneau est libre
            is_available = True
            for reservation in reservations:
                if (reservation.start_time < slot_end and reservation.end_time > current_time):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append({
                    'start_time': current_time,
                    'end_time': slot_end,
                    'duration_minutes': duration_minutes
                })
            
            current_time += timedelta(minutes=30)  # Avancer de 30 minutes
        
        return available_slots
    
    @staticmethod
    def get_terrain_utilization(terrain, start_date, end_date):
        """Calcule le taux d'utilisation d'un terrain sur une période"""
        if not terrain.is_available:
            return {
                'utilization_rate': 0,
                'total_hours': 0,
                'reserved_hours': 0,
                'available_hours': 0
            }
        
        # Calculer le nombre total d'heures disponibles
        total_days = (end_date - start_date).days + 1
        daily_hours = 13  # 9h à 22h = 13 heures par jour
        total_hours = total_days * daily_hours
        
        # Calculer les heures réservées
        reservations = Reservation.objects.filter(
            terrain=terrain,
            status__in=['pending', 'confirmed'],
            start_time__gte=start_date,
            end_time__lte=end_date
        )
        
        reserved_hours = 0
        for reservation in reservations:
            duration = (reservation.end_time - reservation.start_time).total_seconds() / 3600
            reserved_hours += duration
        
        available_hours = total_hours - reserved_hours
        utilization_rate = (reserved_hours / total_hours * 100) if total_hours > 0 else 0
        
        return {
            'utilization_rate': round(utilization_rate, 2),
            'total_hours': total_hours,
            'reserved_hours': round(reserved_hours, 2),
            'available_hours': round(available_hours, 2),
            'reservations_count': reservations.count()
        }

class TerrainSearchService:
    """Service pour la recherche de terrains"""
    
    @staticmethod
    def search_terrains(query=None, terrain_type=None, min_capacity=None, 
                       max_price=None, is_available=None, start_time=None, end_time=None):
        """Recherche avancée de terrains avec filtres multiples"""
        terrains = Terrain.objects.all()
        
        # Filtre par recherche textuelle
        if query:
            terrains = terrains.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
        
        # Filtre par type
        if terrain_type:
            terrains = terrains.filter(terrain_type=terrain_type)
        
        # Filtre par capacité minimale
        if min_capacity:
            terrains = terrains.filter(capacity__gte=min_capacity)
        
        # Filtre par prix maximum
        if max_price:
            terrains = terrains.filter(price_per_hour__lte=max_price)
        
        # Filtre par disponibilité
        if is_available is not None:
            terrains = terrains.filter(is_available=is_available)
        
        # Filtre par disponibilité temporelle
        if start_time and end_time:
            available_terrains = []
            for terrain in terrains:
                availability = TerrainAvailabilityService.check_period_availability(
                    terrain, start_time, end_time
                )
                if availability['available']:
                    available_terrains.append(terrain)
            terrains = available_terrains
        
        return terrains.order_by('name')
    
    @staticmethod
    def get_recommendations(user_preferences=None, limit=5):
        """Recommande des terrains basés sur les préférences utilisateur"""
        terrains = Terrain.objects.filter(is_available=True)
        
        # Si des préférences sont fournies
        if user_preferences:
            # Préférer les types de terrain favoris
            if user_preferences.get('preferred_types'):
                terrains = terrains.filter(
                    terrain_type__in=user_preferences['preferred_types']
                )
            
            # Filtrer par budget
            if user_preferences.get('max_budget'):
                terrains = terrains.filter(
                    price_per_hour__lte=user_preferences['max_budget']
                )
            
            # Filtrer par capacité minimale
            if user_preferences.get('min_capacity'):
                terrains = terrains.filter(
                    capacity__gte=user_preferences['min_capacity']
                )
        
        # Trier par popularité (nombre de réservations) et prix
        from django.db.models import Count
        
        terrains_with_stats = []
        for terrain in terrains:
            reservation_count = Reservation.objects.filter(
                terrain=terrain,
                status__in=['pending', 'confirmed']
            ).count()
            
            terrains_with_stats.append({
                'terrain': terrain,
                'popularity_score': reservation_count,
                'price_score': 1 / (terrain.price_per_hour or 1)
            })
        
        # Trier par score combiné
        terrains_with_stats.sort(
            key=lambda x: x['popularity_score'] * 0.7 + x['price_score'] * 0.3,
            reverse=True
        )
        
        return [item['terrain'] for item in terrains_with_stats[:limit]]
