from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from datetime import datetime, timedelta

from ..serializers.integration_serializer import (
    UserReservationsSerializer, UserActivitiesSerializer, 
    UserDashboardSerializer
)

User = get_user_model()

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_reservations_view(request):
    """Récupérer les réservations de l'utilisateur connecté"""
    serializer = UserReservationsSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_activities_view(request):
    """Récupérer les activités de l'utilisateur connecté"""
    serializer = UserActivitiesSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard_view(request):
    """Tableau de bord de l'utilisateur connecté"""
    serializer = UserDashboardSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_calendar_view(request):
    """Vue calendrier des événements de l'utilisateur"""
    from reservations.models import Reservation
    from activities.models import Activity
    
    # Paramètres de date
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Valeurs par défaut : mois actuel
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        end_date = end_date.strftime('%Y-%m-%d')
    
    # Convertir en datetime
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    events = []
    
    # Réservations dans la période
    reservations = request.user.reservations.filter(
        start_time__gte=start_dt,
        start_time__lte=end_dt,
        status__in=['pending', 'confirmed']
    ).order_by('start_time')
    
    for res in reservations:
        events.append({
            'id': f"reservation_{res.id}",
            'title': f"Réservation - {res.terrain.name}",
            'start': res.start_time.isoformat(),
            'end': res.end_time.isoformat(),
            'type': 'reservation',
            'color': '#3788d8',
            'terrain': res.terrain.name,
            'status': res.status
        })
    
    # Activités où l'utilisateur participe
    participating = request.user.participating_activities.filter(
        start_time__gte=start_dt,
        start_time__lte=end_dt,
        status__in=['pending', 'confirmed']
    ).order_by('start_time')
    
    for activity in participating:
        events.append({
            'id': f"activity_{activity.id}",
            'title': activity.title,
            'start': activity.start_time.isoformat(),
            'end': activity.end_time.isoformat(),
            'type': 'activity',
            'color': '#28a745',
            'role': 'participant',
            'activity_type': activity.activity_type,
            'terrain': activity.terrain.name
        })
    
    # Activités où l'utilisateur est coach
    coaching = request.user.coach_activities.filter(
        start_time__gte=start_dt,
        start_time__lte=end_dt,
        status__in=['pending', 'confirmed']
    ).order_by('start_time')
    
    for activity in coaching:
        events.append({
            'id': f"coaching_{activity.id}",
            'title': f"[COACH] {activity.title}",
            'start': activity.start_time.isoformat(),
            'end': activity.end_time.isoformat(),
            'type': 'activity',
            'color': '#dc3545',
            'role': 'coach',
            'activity_type': activity.activity_type,
            'terrain': activity.terrain.name
        })
    
    return Response(events)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats_view(request):
    """Statistiques détaillées de l'utilisateur"""
    from reservations.models import Reservation
    from activities.models import Activity
    
    # Période pour les statistiques
    days = int(request.GET.get('days', 30))
    start_date = datetime.now() - timedelta(days=days)
    
    # Statistiques des réservations
    total_reservations = request.user.reservations.count()
    recent_reservations = request.user.reservations.filter(
        created_at__gte=start_date
    ).count()
    
    # Réservations par statut
    reservations_by_status = request.user.reservations.values('status').annotate(
        count=Count('id')
    )
    
    # Statistiques des activités
    total_participating = request.user.participating_activities.count()
    total_coaching = request.user.coach_activities.count()
    
    recent_participating = request.user.participating_activities.filter(
        created_at__gte=start_date
    ).count()
    
    recent_coaching = request.user.coach_activities.filter(
        created_at__gte=start_date
    ).count()
    
    # Terrains préférés
    favorite_terrains = request.user.reservations.values(
        'terrain__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Activités par type
    activities_by_type = request.user.participating_activities.values(
        'activity_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    return Response({
        'period_days': days,
        'reservations': {
            'total': total_reservations,
            'recent': recent_reservations,
            'by_status': list(reservations_by_status),
            'favorite_terrains': list(favorite_terrains)
        },
        'activities': {
            'participating': {
                'total': total_participating,
                'recent': recent_participating
            },
            'coaching': {
                'total': total_coaching,
                'recent': recent_coaching
            },
            'by_type': list(activities_by_type)
        }
    })

class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les activités liées à l'utilisateur"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Retourne les activités pertinentes pour l'utilisateur"""
        user = self.request.user
        return user.participating_activities.union(user.coach_activities).distinct()
    
    @action(detail=False, methods=['get'])
    def participating(self, request):
        """Activités où l'utilisateur participe"""
        activities = request.user.participating_activities.all()
        from activities.api.serializers import ActivitySerializer
        serializer = ActivitySerializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def coaching(self, request):
        """Activités où l'utilisateur est coach"""
        if request.user.role != 'coach' and not request.user.is_staff:
            return Response(
                {'error': 'Vous devez être coach pour voir ces activités'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        activities = request.user.coach_activities.all()
        from activities.api.serializers import ActivitySerializer
        serializer = ActivitySerializer(activities, many=True)
        return Response(serializer.data)
