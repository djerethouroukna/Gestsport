from rest_framework import serializers
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta

User = get_user_model()

class UserReservationsSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les réservations d'un utilisateur"""
    reservations_count = serializers.SerializerMethodField()
    upcoming_reservations = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 
                 'reservations_count', 'upcoming_reservations')
    
    def get_reservations_count(self, obj):
        """Nombre total de réservations"""
        return obj.reservations.count()
    
    def get_upcoming_reservations(self, obj):
        """Réservations à venir"""
        from reservations.models import Reservation
        now = datetime.now()
        upcoming = obj.reservations.filter(
            start_time__gt=now,
            status__in=['pending', 'confirmed']
        ).order_by('start_time')[:3]
        
        return [
            {
                'id': res.id,
                'terrain': res.terrain.name,
                'start_time': res.start_time,
                'end_time': res.end_time,
                'status': res.status
            }
            for res in upcoming
        ]

class UserActivitiesSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les activités d'un utilisateur"""
    participating_count = serializers.SerializerMethodField()
    coaching_count = serializers.SerializerMethodField()
    upcoming_activities = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email',
                 'participating_count', 'coaching_count', 'upcoming_activities')
    
    def get_participating_count(self, obj):
        """Nombre d'activités où l'utilisateur participe"""
        return obj.participating_activities.count()
    
    def get_coaching_count(self, obj):
        """Nombre d'activités où l'utilisateur est coach"""
        return obj.coach_activities.count()
    
    def get_upcoming_activities(self, obj):
        """Activités à venir"""
        from activities.models import Activity
        now = datetime.now()
        
        # Activités où l'utilisateur participe
        participating = obj.participating_activities.filter(
            start_time__gt=now,
            status__in=['pending', 'confirmed']
        )
        
        # Activités où l'utilisateur est coach
        coaching = obj.coach_activities.filter(
            start_time__gt=now,
            status__in=['pending', 'confirmed']
        )
        
        # Combiner et trier
        all_activities = (participating | coaching).distinct().order_by('start_time')[:3]
        
        return [
            {
                'id': activity.id,
                'title': activity.title,
                'activity_type': activity.activity_type,
                'start_time': activity.start_time,
                'end_time': activity.end_time,
                'terrain': activity.terrain.name,
                'role': 'coach' if activity.coach == obj else 'participant'
            }
            for activity in all_activities
        ]

class UserDashboardSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le dashboard utilisateur"""
    stats = serializers.SerializerMethodField()
    upcoming_events = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'role',
                 'stats', 'upcoming_events')
    
    def get_stats(self, obj):
        """Statistiques de l'utilisateur"""
        from reservations.models import Reservation
        from activities.models import Activity
        
        # Réservations
        total_reservations = obj.reservations.count()
        this_month_reservations = obj.reservations.filter(
            start_time__month=datetime.now().month,
            start_time__year=datetime.now().year
        ).count()
        
        # Activités
        participating_activities = obj.participating_activities.count()
        coaching_activities = obj.coach_activities.count()
        
        return {
            'reservations': {
                'total': total_reservations,
                'this_month': this_month_reservations
            },
            'activities': {
                'participating': participating_activities,
                'coaching': coaching_activities
            }
        }
    
    def get_upcoming_events(self, obj):
        """Événements à venir (réservations + activités)"""
        from reservations.models import Reservation
        from activities.models import Activity
        
        now = datetime.now()
        events = []
        
        # Réservations à venir
        reservations = obj.reservations.filter(
            start_time__gt=now,
            status__in=['pending', 'confirmed']
        ).order_by('start_time')[:5]
        
        for res in reservations:
            events.append({
                'type': 'reservation',
                'id': res.id,
                'title': f'Réservation - {res.terrain.name}',
                'start_time': res.start_time,
                'end_time': res.end_time,
                'status': res.status
            })
        
        # Activités à venir
        activities = obj.participating_activities.filter(
            start_time__gt=now,
            status__in=['pending', 'confirmed']
        ).order_by('start_time')[:5]
        
        for activity in activities:
            events.append({
                'type': 'activity',
                'id': activity.id,
                'title': activity.title,
                'start_time': activity.start_time,
                'end_time': activity.end_time,
                'status': activity.status,
                'role': 'participant'
            })
        
        # Activités où l'utilisateur est coach
        coaching = obj.coach_activities.filter(
            start_time__gt=now,
            status__in=['pending', 'confirmed']
        ).order_by('start_time')[:5]
        
        for activity in coaching:
            events.append({
                'type': 'activity',
                'id': activity.id,
                'title': activity.title,
                'start_time': activity.start_time,
                'end_time': activity.end_time,
                'status': activity.status,
                'role': 'coach'
            })
        
        # Trier par date
        events.sort(key=lambda x: x['start_time'])
        
        return events[:10]  # Limiter à 10 événements
