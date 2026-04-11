from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Activity, ActivityType, ActivityStatus
from terrains.models import Terrain

User = get_user_model()

class ActivitySerializer(serializers.ModelSerializer):
    """Sérialiseur pour les activités"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    coach_name = serializers.CharField(source='coach.get_full_name', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    participants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = (
            'id', 'title', 'description', 'activity_type', 'activity_type_display',
            'terrain', 'terrain_name', 'coach', 'coach_name', 'start_time',
            'end_time', 'status', 'status_display', 'participants_count',
            'max_participants', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'coach', 'created_at', 'updated_at')
    
    def get_participants_count(self, obj):
        return obj.participants.count()

class ActivityCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer une activité"""
    max_participants = serializers.IntegerField(default=10, min_value=1, max_value=50)
    
    class Meta:
        model = Activity
        fields = (
            'title', 'description', 'activity_type', 'terrain',
            'start_time', 'end_time', 'max_participants'
        )
    
    def validate(self, attrs):
        """Valider la création d'activité"""
        terrain = attrs['terrain']
        start_time = attrs['start_time']
        end_time = attrs['end_time']
        
        # Vérifier que la date de fin est après la date de début
        if end_time <= start_time:
            raise serializers.ValidationError("La date de fin doit être après la date de début.")
        
        # Vérifier que l'activité n'est pas dans le passé
        from django.utils import timezone
        if start_time < timezone.now():
            raise serializers.ValidationError("Impossible de créer une activité pour une date passée.")
        
        # Vérifier la disponibilité du terrain avec d'autres activités
        overlapping_activities = Activity.objects.filter(
            terrain=terrain,
            status=ActivityStatus.CONFIRMED,
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if overlapping_activities.exists():
            raise serializers.ValidationError("Ce terrain n'est pas disponible pour cette période (conflit avec une autre activité).")
        
        # Vérifier la disponibilité du terrain avec les réservations
        from reservations.models import Reservation, ReservationStatus
        overlapping_reservations = Reservation.objects.filter(
            terrain=terrain,
            status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if overlapping_reservations.exists():
            raise serializers.ValidationError("Ce terrain n'est pas disponible pour cette période (conflit avec une réservation).")
        
        return attrs

class ActivityUpdateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour mettre à jour une activité"""
    
    class Meta:
        model = Activity
        fields = ('title', 'description', 'terrain', 'start_time', 'end_time')
    
    def validate(self, attrs):
        """Valider les modifications"""
        instance = self.instance
        
        # Si les dates sont modifiées, vérifier la disponibilité
        if 'start_time' in attrs or 'end_time' in attrs:
            start_time = attrs.get('start_time', instance.start_time)
            end_time = attrs.get('end_time', instance.end_time)
            
            # Vérifier que la date de fin est après la date de début
            if end_time <= start_time:
                raise serializers.ValidationError("La date de fin doit être après la date de début.")
            
            # Vérifier la disponibilité (exclure cette activité)
            overlapping_activities = Activity.objects.filter(
                terrain=attrs.get('terrain', instance.terrain),
                status=ActivityStatus.CONFIRMED,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exclude(id=instance.id)
            
            if overlapping_activities.exists():
                raise serializers.ValidationError("Ce terrain n'est pas disponible pour cette période.")
        
        return attrs

class ActivityListSerializer(serializers.ModelSerializer):
    """Sérialiseur pour lister les activités"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    coach_name = serializers.CharField(source='coach.get_full_name', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    participants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = (
            'id', 'title', 'activity_type', 'activity_type_display',
            'terrain_name', 'coach_name', 'start_time', 'end_time',
            'status', 'status_display', 'participants_count', 'max_participants'
        )
    
    def get_participants_count(self, obj):
        return obj.participants.count()

class ActivityDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les détails d'une activité"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    coach_name = serializers.CharField(source='coach.get_full_name', read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    participants = serializers.SerializerMethodField()
    
    class Meta:
        model = Activity
        fields = (
            'id', 'title', 'description', 'activity_type', 'activity_type_display',
            'terrain', 'terrain_name', 'coach', 'coach_name', 'start_time',
            'end_time', 'status', 'status_display', 'participants',
            'max_participants', 'created_at', 'updated_at'
        )
    
    def get_participants(self, obj):
        participants = obj.participants.all()
        return [
            {
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'role': user.role
            }
            for user in participants
        ]

class ActivityJoinSerializer(serializers.Serializer):
    """Sérialiseur pour rejoindre/quitter une activité"""
    action = serializers.ChoiceField(choices=['join', 'leave'])

class ActivityStatusSerializer(serializers.Serializer):
    """Sérialiseur pour changer le statut d'une activité"""
    status = serializers.ChoiceField(choices=ActivityStatus.choices)

class ActivitySearchSerializer(serializers.Serializer):
    """Sérialiseur pour la recherche d'activités"""
    terrain = serializers.IntegerField(required=False)
    coach = serializers.IntegerField(required=False)
    activity_type = serializers.ChoiceField(choices=ActivityType.choices, required=False)
    status = serializers.ChoiceField(choices=ActivityStatus.choices, required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
