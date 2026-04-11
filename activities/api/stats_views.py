from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q, Sum
from django.db import models

from activities.models import Activity, ActivityType, ActivityStatus
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def activity_statistics_view(request):
    """Statistiques générales sur les activités"""
    
    # Période par défaut : 30 derniers jours
    days = int(request.GET.get('days', 30))
    date_from = timezone.now() - timedelta(days=days)
    
    queryset = Activity.objects.filter(start_time__gte=date_from)
    
    # Statistiques par type
    stats_by_type = []
    for activity_type, display_name in ActivityType.choices:
        count = queryset.filter(activity_type=activity_type).count()
        stats_by_type.append({
            'type': activity_type,
            'display_name': display_name,
            'count': count
        })
    
    # Statistiques par statut
    stats_by_status = []
    for status, display_name in ActivityStatus.choices:
        count = queryset.filter(status=status).count()
        stats_by_status.append({
            'status': status,
            'display_name': display_name,
            'count': count
        })
    
    # Statistiques de participation
    activities_with_participants = queryset.annotate(
        participants_count=Count('participants')
    )
    
    total_activities = activities_with_participants.count()
    total_participants = activities_with_participants.aggregate(
        total=Sum('participants_count')
    )['total'] or 0
    
    total_capacity = queryset.aggregate(
        total=Sum('max_participants')
    )['total'] or 0
    
    avg_participants_per_activity = total_participants / total_activities if total_activities > 0 else 0
    avg_capacity_usage = (total_participants / total_capacity * 100) if total_capacity > 0 else 0
    
    # Top 5 des coachs les plus actifs
    top_coaches = queryset.values('coach__id', 'coach__first_name', 'coach__last_name').annotate(
        activity_count=Count('id')
    ).order_by('-activity_count')[:5]
    
    # Top 5 des terrains les plus utilisés
    top_terrains = queryset.values('terrain__id', 'terrain__name').annotate(
        activity_count=Count('id')
    ).order_by('-activity_count')[:5]
    
    return Response({
        'period': {
            'days': days,
            'from': date_from.isoformat(),
            'to': timezone.now().isoformat()
        },
        'summary': {
            'total_activities': total_activities,
            'total_participants': total_participants,
            'total_capacity': total_capacity,
            'avg_participants_per_activity': round(avg_participants_per_activity, 2),
            'capacity_usage_percentage': round(avg_capacity_usage, 2)
        },
        'stats_by_type': stats_by_type,
        'stats_by_status': stats_by_status,
        'top_coaches': list(top_coaches),
        'top_terrains': list(top_terrains)
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def coach_statistics_view(request, coach_id=None):
    """Statistiques pour un coach spécifique"""
    
    if coach_id:
        try:
            coach = User.objects.get(id=coach_id, role='coach')
        except User.DoesNotExist:
            return Response(
                {'error': 'Coach non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        coach = request.user
        if coach.role != 'coach':
            return Response(
                {'error': 'Accès réservé aux coachs'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Période par défaut : 30 derniers jours
    days = int(request.GET.get('days', 30))
    date_from = timezone.now() - timedelta(days=days)
    
    queryset = Activity.objects.filter(coach=coach, start_time__gte=date_from)
    
    # Statistiques par type
    stats_by_type = []
    for activity_type, display_name in ActivityType.choices:
        count = queryset.filter(activity_type=activity_type).count()
        stats_by_type.append({
            'type': activity_type,
            'display_name': display_name,
            'count': count
        })
    
    # Statistiques de participation
    activities_with_participants = queryset.annotate(
        participants_count=Count('participants')
    )
    
    total_activities = activities_with_participants.count()
    total_participants = activities_with_participants.aggregate(
        total=Sum('participants_count')
    )['total'] or 0
    
    total_capacity = queryset.aggregate(
        total=Sum('max_participants')
    )['total'] or 0
    
    avg_participants_per_activity = total_participants / total_activities if total_activities > 0 else 0
    avg_capacity_usage = (total_participants / total_capacity * 100) if total_capacity > 0 else 0
    
    # Évolution mensuelle
    monthly_stats = []
    for i in range(6):
        month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_activities = queryset.filter(
            start_time__gte=month_start,
            start_time__lte=month_end
        )
        
        monthly_stats.append({
            'month': month_start.strftime('%Y-%m'),
            'activities_count': month_activities.count(),
            'participants_total': month_activities.aggregate(
                total=Sum('participants__count')
            )['total'] or 0
        })
    
    monthly_stats.reverse()
    
    return Response({
        'coach': {
            'id': coach.id,
            'name': coach.get_full_name(),
            'email': coach.email
        },
        'period': {
            'days': days,
            'from': date_from.isoformat(),
            'to': timezone.now().isoformat()
        },
        'summary': {
            'total_activities': total_activities,
            'total_participants': total_participants,
            'total_capacity': total_capacity,
            'avg_participants_per_activity': round(avg_participants_per_activity, 2),
            'capacity_usage_percentage': round(avg_capacity_usage, 2)
        },
        'stats_by_type': stats_by_type,
        'monthly_evolution': monthly_stats
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def terrain_statistics_view(request, terrain_id=None):
    """Statistiques pour un terrain spécifique"""
    
    if terrain_id:
        try:
            from terrains.models import Terrain
            terrain = Terrain.objects.get(id=terrain_id)
        except Terrain.DoesNotExist:
            return Response(
                {'error': 'Terrain non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        # Statistiques pour tous les terrains
        terrain = None
    
    # Période par défaut : 30 derniers jours
    days = int(request.GET.get('days', 30))
    date_from = timezone.now() - timedelta(days=days)
    
    queryset = Activity.objects.filter(start_time__gte=date_from)
    if terrain:
        queryset = queryset.filter(terrain=terrain)
    
    # Taux d'occupation par heure
    occupation_by_hour = []
    for hour in range(9, 23):  # 9h à 22h
        hour_activities = queryset.filter(start_time__hour=hour)
        total_hours = (timezone.now() - date_from).total_seconds() / 3600
        occupation_rate = (hour_activities.count() / total_hours * 100) if total_hours > 0 else 0
        
        occupation_by_hour.append({
            'hour': hour,
            'activities_count': hour_activities.count(),
            'occupation_rate': round(occupation_rate, 2)
        })
    
    # Types d'activités les plus populaires
    popular_types = queryset.values('activity_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Jours les plus actifs
    active_days = queryset.extra(
        select={'day': 'date(start_time)'}
    ).values('day').annotate(
        count=Count('id')
    ).order_by('-count')[:7]
    
    return Response({
        'terrain': {
            'id': terrain.id if terrain else None,
            'name': terrain.name if terrain else 'Tous les terrains'
        },
        'period': {
            'days': days,
            'from': date_from.isoformat(),
            'to': timezone.now().isoformat()
        },
        'occupation_by_hour': occupation_by_hour,
        'popular_types': list(popular_types),
        'most_active_days': list(active_days),
        'total_activities': queryset.count()
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def participation_trends_view(request):
    """Tendances de participation"""
    
    # Période par défaut : 90 derniers jours
    days = int(request.GET.get('days', 90))
    date_from = timezone.now() - timedelta(days=days)
    
    queryset = Activity.objects.filter(start_time__gte=date_from)
    
    # Évolution hebdomadaire
    weekly_stats = []
    current_date = date_from
    
    while current_date <= timezone.now():
        week_start = current_date
        week_end = week_start + timedelta(days=7)
        
        week_activities = queryset.filter(
            start_time__gte=week_start,
            start_time__lt=week_end
        )
        
        week_participants = week_activities.aggregate(
            participants_total=Sum('participants__count')
        )['participants_total'] or 0
        
        weekly_stats.append({
            'week': week_start.strftime('%Y-%W'),
            'activities_count': week_activities.count(),
            'participants_total': week_participants,
            'avg_participants_per_activity': (
                week_participants / week_activities.count()
                if week_activities.count() > 0 else 0
            )
        })
        
        current_date = week_end
    
    return Response({
        'period': {
            'days': days,
            'from': date_from.isoformat(),
            'to': timezone.now().isoformat()
        },
        'weekly_trends': weekly_stats
    })
