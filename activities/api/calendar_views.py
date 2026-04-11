from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q, Count
from django.db import models

from terrains.models import Terrain
from activities.models import Activity, ActivityStatus, ActivityType
from reservations.models import Reservation, ReservationStatus

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def activity_calendar_view(request):
    """Vue calendrier pour voir les activités et disponibilités"""
    
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
        terrain_data = {
            'terrain_id': terrain.id,
            'terrain_name': terrain.name,
            'hours': []
        }
        
        for hour in hours:
            hour_start = timezone.make_aware(
                datetime.combine(target_date, datetime.min.time().replace(hour=hour))
            )
            hour_end = hour_start + timedelta(hours=1)
            
            # Vérifier les activités
            activities = Activity.objects.filter(
                terrain=terrain,
                start_time__lt=hour_end,
                end_time__gt=hour_start,
                status=ActivityStatus.CONFIRMED
            )
            
            # Vérifier les réservations
            reservations = Reservation.objects.filter(
                terrain=terrain,
                start_time__lt=hour_end,
                end_time__gt=hour_start,
                status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING]
            )
            
            hour_data = {
                'hour': hour,
                'activities': [
                    {
                        'id': activity.id,
                        'title': activity.title,
                        'activity_type': activity.activity_type,
                        'coach': activity.coach.get_full_name(),
                        'participants_count': activity.participants.count(),
                        'max_participants': activity.max_participants,
                        'start_time': activity.start_time,
                        'end_time': activity.end_time
                    } for activity in activities
                ],
                'reservations': [
                    {
                        'id': reservation.id,
                        'user': reservation.user.get_full_name(),
                        'start_time': reservation.start_time,
                        'end_time': reservation.end_time,
                        'status': reservation.status
                    } for reservation in reservations
                ],
                'is_available': not activities.exists() and not reservations.exists()
            }
            
            terrain_data['hours'].append(hour_data)
        
        calendar_data.append(terrain_data)
    
    return Response({
        'date': target_date.strftime('%Y-%m-%d'),
        'terrains': calendar_data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def activity_conflicts_view(request):
    """Vérifier les conflits pour une nouvelle activité"""
    
    terrain_id = request.GET.get('terrain_id')
    start_time_str = request.GET.get('start_time')
    end_time_str = request.GET.get('end_time')
    
    if not all([terrain_id, start_time_str, end_time_str]):
        return Response(
            {'error': 'Paramètres manquants: terrain_id, start_time, end_time'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        terrain = Terrain.objects.get(id=terrain_id)
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    except (Terrain.DoesNotExist, ValueError) as e:
        return Response(
            {'error': f'Paramètres invalides: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier les conflits avec d'autres activités
    activity_conflicts = Activity.objects.filter(
        terrain=terrain,
        start_time__lt=end_time,
        end_time__gt=start_time,
        status=ActivityStatus.CONFIRMED
    )
    
    # Vérifier les conflits avec les réservations
    reservation_conflicts = Reservation.objects.filter(
        terrain=terrain,
        start_time__lt=end_time,
        end_time__gt=start_time,
        status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING]
    )
    
    conflicts = []
    
    for activity in activity_conflicts:
        conflicts.append({
            'type': 'activity',
            'id': activity.id,
            'title': activity.title,
            'coach': activity.coach.get_full_name(),
            'start_time': activity.start_time,
            'end_time': activity.end_time
        })
    
    for reservation in reservation_conflicts:
        conflicts.append({
            'type': 'reservation',
            'id': reservation.id,
            'user': reservation.user.get_full_name(),
            'start_time': reservation.start_time,
            'end_time': reservation.end_time,
            'status': reservation.status
        })
    
    return Response({
        'has_conflicts': len(conflicts) > 0,
        'conflicts': conflicts,
        'is_available': len(conflicts) == 0
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def activity_availability_summary(request):
    """Résumé des disponibilités pour les activités"""
    
    # Paramètres
    date_from_str = request.GET.get('date_from')
    date_to_str = request.GET.get('date_to')
    terrain_id = request.GET.get('terrain_id')
    
    # Période par défaut : cette semaine
    if date_from_str:
        try:
            date_from = datetime.fromisoformat(date_from_str.replace('Z', '+00:00'))
        except ValueError:
            date_from = timezone.now()
    else:
        date_from = timezone.now()
    
    if date_to_str:
        try:
            date_to = datetime.fromisoformat(date_to_str.replace('Z', '+00:00'))
        except ValueError:
            date_to = date_from + timedelta(days=7)
    else:
        date_to = date_from + timedelta(days=7)
    
    # Filtrer par terrain si spécifié
    terrain_filter = {}
    if terrain_id:
        terrain_filter['terrain_id'] = int(terrain_id)
    
    # Obtenir les statistiques
    queryset = Activity.objects.filter(
        start_time__gte=date_from,
        start_time__lte=date_to,
        **terrain_filter
    )
    
    # Statistiques par type
    stats_by_type = {}
    for activity_type, _ in ActivityType.choices:
        count = queryset.filter(activity_type=activity_type).count()
        stats_by_type[activity_type] = count
    
    # Statistiques par statut
    stats_by_status = {}
    for status, _ in ActivityStatus.choices:
        count = queryset.filter(status=status).count()
        stats_by_status[status] = count
    
    # Taux de participation moyen
    activities_with_participants = queryset.annotate(
        participants_count=models.Count('participants')
    )
    
    total_slots = sum(activity.max_participants for activity in activities_with_participants)
    total_participants = sum(activity.participants_count for activity in activities_with_participants)
    avg_participation_rate = (total_participants / total_slots * 100) if total_slots > 0 else 0
    
    return Response({
        'period': {
            'from': date_from.isoformat(),
            'to': date_to.isoformat()
        },
        'total_activities': queryset.count(),
        'stats_by_type': stats_by_type,
        'stats_by_status': stats_by_status,
        'avg_participation_rate': round(avg_participation_rate, 2),
        'total_participants': total_participants,
        'total_capacity': total_slots
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def available_slots_view(request):
    """Créneaux disponibles pour créer des activités"""
    
    terrain_id = request.GET.get('terrain_id')
    date_str = request.GET.get('date')
    duration_hours = int(request.GET.get('duration', 1))
    
    if not terrain_id or not date_str:
        return Response(
            {'error': 'Paramètres requis: terrain_id, date'},
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
    
    # Heures d'ouverture
    start_hour = 9
    end_hour = 22
    
    available_slots = []
    
    for hour in range(start_hour, end_hour - duration_hours + 1):
        slot_start = timezone.make_aware(
            datetime.combine(target_date, datetime.min.time().replace(hour=hour))
        )
        slot_end = slot_start + timedelta(hours=duration_hours)
        
        # Vérifier les conflits
        activity_conflicts = Activity.objects.filter(
            terrain=terrain,
            start_time__lt=slot_end,
            end_time__gt=slot_start,
            status=ActivityStatus.CONFIRMED
        ).exists()
        
        reservation_conflicts = Reservation.objects.filter(
            terrain=terrain,
            start_time__lt=slot_end,
            end_time__gt=slot_start,
            status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING]
        ).exists()
        
        if not activity_conflicts and not reservation_conflicts:
            available_slots.append({
                'start_time': slot_start.isoformat(),
                'end_time': slot_end.isoformat(),
                'duration_hours': duration_hours
            })
    
    return Response({
        'terrain': terrain.name,
        'date': date_str,
        'duration_hours': duration_hours,
        'available_slots': available_slots
    })
