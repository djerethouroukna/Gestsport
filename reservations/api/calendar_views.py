from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q

from terrains.models import Terrain
from reservations.models import Reservation, ReservationStatus
from terrains.utils import TerrainAvailabilityService

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def calendar_view(request):
    """Vue calendrier simple pour voir les disponibilités des terrains"""
    
    # Paramètres de la requête
    date_str = request.GET.get('date')
    terrain_id = request.GET.get('terrain_id')
    
    # Date par défaut : aujourd'hui
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        target_date = timezone.now().date()
    
    # Filtrer par terrain si spécifié
    if terrain_id:
        try:
            terrains = [Terrain.objects.get(id=terrain_id)]
        except Terrain.DoesNotExist:
            return Response(
                {'error': 'Terrain non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        terrains = Terrain.objects.filter(is_available=True)
    
    # Heures d'ouverture (9h-22h)
    start_hour = 9
    end_hour = 22
    hours = list(range(start_hour, end_hour + 1))
    
    calendar_data = []
    
    for terrain in terrains:
        # Récupérer les réservations pour ce terrain à la date spécifiée
        reservations = Reservation.objects.filter(
            terrain=terrain,
            start_time__date=target_date,
            status__in=['pending', 'confirmed']
        ).order_by('start_time')
        
        # Créer la grille horaire
        hourly_status = []
        
        for hour in hours:
            hour_start = timezone.make_aware(
                datetime.combine(target_date, datetime.min.time()).replace(hour=hour)
            )
            hour_end = hour_start + timedelta(hours=1)
            
            # Vérifier si le terrain est occupé pendant cette heure
            is_occupied = False
            reservation_info = None
            
            for reservation in reservations:
                # Vérifier si la réservation chevauche cette heure
                if (reservation.start_time < hour_end and reservation.end_time > hour_start):
                    is_occupied = True
                    reservation_info = {
                        'id': reservation.id,
                        'user_name': reservation.user.get_full_name(),
                        'start_time': reservation.start_time,
                        'end_time': reservation.end_time,
                        'status': reservation.status
                    }
                    break
            
            hourly_status.append({
                'hour': hour,
                'is_available': not is_occupied,
                'reservation': reservation_info
            })
        
        # Calculer les statistiques du jour
        total_hours = len(hours)
        occupied_hours = sum(1 for h in hourly_status if not h['is_available'])
        available_hours = total_hours - occupied_hours
        availability_rate = (available_hours / total_hours * 100) if total_hours > 0 else 0
        
        calendar_data.append({
            'terrain': {
                'id': terrain.id,
                'name': terrain.name,
                'type': terrain.get_terrain_type_display(),
                'capacity': terrain.capacity,
                'price_per_hour': float(terrain.price_per_hour)
            },
            'date': target_date.strftime('%Y-%m-%d'),
            'hours': hourly_status,
            'statistics': {
                'total_hours': total_hours,
                'available_hours': available_hours,
                'occupied_hours': occupied_hours,
                'availability_rate': round(availability_rate, 1)
            }
        })
    
    return Response({
        'date': target_date.strftime('%Y-%m-%d'),
        'hours_range': f"{start_hour}h-{end_hour}h",
        'terrains': calendar_data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def terrain_availability_summary(request):
    """Résumé des disponibilités par terrain pour aujourd'hui et demain"""
    
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    
    terrains = Terrain.objects.filter(is_available=True)
    summary_data = []
    
    for terrain in terrains:
        # Statistiques pour aujourd'hui
        today_stats = TerrainAvailabilityService.get_terrain_utilization(
            terrain, 
            timezone.make_aware(datetime.combine(today, datetime.min.time())),
            timezone.make_aware(datetime.combine(today, datetime.max.time()))
        )
        
        # Statistiques pour demain
        tomorrow_stats = TerrainAvailabilityService.get_terrain_utilization(
            terrain,
            timezone.make_aware(datetime.combine(tomorrow, datetime.min.time())),
            timezone.make_aware(datetime.combine(tomorrow, datetime.max.time()))
        )
        
        # Prochaines réservations
        next_reservation = Reservation.objects.filter(
            terrain=terrain,
            status__in=['pending', 'confirmed'],
            start_time__gt=timezone.now()
        ).order_by('start_time').first()
        
        summary_data.append({
            'terrain': {
                'id': terrain.id,
                'name': terrain.name,
                'type': terrain.get_terrain_type_display(),
                'capacity': terrain.capacity,
                'price_per_hour': float(terrain.price_per_hour)
            },
            'today': {
                'availability_rate': today_stats['utilization_rate'],
                'available_hours': today_stats['available_hours'],
                'total_hours': today_stats['total_hours']
            },
            'tomorrow': {
                'availability_rate': tomorrow_stats['utilization_rate'],
                'available_hours': tomorrow_stats['available_hours'],
                'total_hours': tomorrow_stats['total_hours']
            },
            'next_reservation': {
                'id': next_reservation.id,
                'start_time': next_reservation.start_time,
                'user_name': next_reservation.user.get_full_name()
            } if next_reservation else None,
            'is_available_now': TerrainAvailabilityService.is_available_now(terrain)
        })
    
    return Response({
        'summary_date': today.strftime('%Y-%m-%d'),
        'terrains': summary_data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def available_slots(request):
    """Créneaux disponibles pour un terrain et une date spécifiques"""
    
    terrain_id = request.GET.get('terrain_id')
    date_str = request.GET.get('date')
    duration = int(request.GET.get('duration', 60))  # Durée en minutes
    
    if not terrain_id or not date_str:
        return Response(
            {'error': 'terrain_id et date sont obligatoires'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        terrain = Terrain.objects.get(id=terrain_id)
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (Terrain.DoesNotExist, ValueError):
        return Response(
            {'error': 'Paramètres invalides'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not terrain.is_available:
        return Response({
            'terrain': terrain.name,
            'date': date_str,
            'available_slots': [],
            'message': 'Ce terrain n\'est pas disponible'
        })
    
    # Utiliser le service pour obtenir les créneaux disponibles
    available_slots = TerrainAvailabilityService.get_available_slots(
        terrain, target_date, duration
    )
    
    return Response({
        'terrain': {
            'id': terrain.id,
            'name': terrain.name,
            'type': terrain.get_terrain_type_display(),
            'price_per_hour': float(terrain.price_per_hour)
        },
        'date': date_str,
        'duration_minutes': duration,
        'available_slots': [
            {
                'start_time': slot['start_time'].strftime('%H:%M'),
                'end_time': slot['end_time'].strftime('%H:%M'),
                'price': float(terrain.price_per_hour * duration / 60)
            }
            for slot in available_slots
        ],
        'total_slots': len(available_slots)
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reservation_conflicts(request):
    """Vérifier les conflits potentiels pour une réservation"""
    
    terrain_id = request.GET.get('terrain_id')
    start_time_str = request.GET.get('start_time')
    end_time_str = request.GET.get('end_time')
    
    if not all([terrain_id, start_time_str, end_time_str]):
        return Response(
            {'error': 'terrain_id, start_time et end_time sont obligatoires'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        terrain = Terrain.objects.get(id=terrain_id)
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    except (Terrain.DoesNotExist, ValueError):
        return Response(
            {'error': 'Paramètres invalides'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier les conflits
    availability = TerrainAvailabilityService.check_period_availability(
        terrain, start_time, end_time
    )
    
    return Response({
        'terrain': {
            'id': terrain.id,
            'name': terrain.name
        },
        'requested_period': {
            'start_time': start_time_str,
            'end_time': end_time_str
        },
        'is_available': availability['available'],
        'reason': availability['reason'],
        'conflicts': availability['conflicts']
    })
