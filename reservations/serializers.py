from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Reservation, ReservationStatus
from terrains.models import Terrain

User = get_user_model()

class ReservationSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les réservations"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Reservation
        fields = (
            'id', 'user', 'user_name', 'terrain', 'terrain_name',
            'start_time', 'end_time', 'status', 'status_display',
            'notes', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

class ReservationCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer une réservation"""
    
    class Meta:
        model = Reservation
        fields = ('terrain', 'start_time', 'end_time', 'notes')
    
    def validate(self, attrs):
        """Valider la disponibilité du terrain"""
        terrain = attrs['terrain']
        start_time = attrs['start_time']
        end_time = attrs['end_time']
        
        # Vérifier que la date de fin est après la date de début
        if end_time <= start_time:
            raise serializers.ValidationError("La date de fin doit être après la date de début.")
        
        # Vérifier que la réservation n'est pas dans le passé
        from django.utils import timezone
        if start_time < timezone.now():
            raise serializers.ValidationError("Impossible de réserver pour une date passée.")
        
        # Vérifier la disponibilité du terrain
        overlapping_reservations = Reservation.objects.filter(
            terrain=terrain,
            status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if overlapping_reservations.exists():
            raise serializers.ValidationError("Ce terrain n'est pas disponible pour cette période.")
        
        return attrs

class ReservationUpdateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour mettre à jour une réservation"""
    
    class Meta:
        model = Reservation
        fields = ('start_time', 'end_time', 'notes')
    
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
            
            # Vérifier la disponibilité (exclure cette réservation)
            overlapping_reservations = Reservation.objects.filter(
                terrain=instance.terrain,
                status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exclude(id=instance.id)
            
            if overlapping_reservations.exists():
                raise serializers.ValidationError("Ce terrain n'est pas disponible pour cette période.")
        
        return attrs

class ReservationListSerializer(serializers.ModelSerializer):
    """Sérialiseur pour lister les réservations avec toutes les données nécessaires"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    terrain_type = serializers.CharField(source='terrain.terrain_type', read_only=True)
    terrain_capacity = serializers.IntegerField(source='terrain.capacity', read_only=True)
    terrain_price_per_hour = serializers.DecimalField(source='terrain.price_per_hour', max_digits=10, decimal_places=2, read_only=True)
    terrain_status = serializers.CharField(source='terrain.status', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_price = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Reservation
        fields = (
            'id', 'user', 'user_name', 'user_email', 'user_role', 'user_phone',
            'terrain', 'terrain_name', 'terrain_type', 'terrain_capacity', 
            'terrain_price_per_hour', 'terrain_status',
            'start_time', 'end_time', 'status', 'status_display',
            'total_price', 'payment_status', 'notes', 'created_at', 'updated_at'
        )
    
    def get_total_price(self, obj):
        """Calcule le prix total de la réservation"""
        if hasattr(obj, 'total_amount'):
            return obj.total_amount
        # Calcul manuel si la propriété n'existe pas
        from decimal import Decimal
        duration = obj.end_time - obj.start_time
        hours = Decimal(str(duration.total_seconds() / 3600))
        return hours * obj.terrain.price_per_hour
    
    def get_payment_status(self, obj):
        """Retourne le statut du paiement"""
        if hasattr(obj, 'payment_status'):
            return obj.payment_status
        return 'pending'  # Valeur par défaut

class ReservationStatusSerializer(serializers.Serializer):
    """Sérialiseur pour changer le statut d'une réservation"""
    status = serializers.ChoiceField(choices=ReservationStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)

class ReservationSearchSerializer(serializers.Serializer):
    """Sérialiseur pour la recherche de réservations"""
    terrain = serializers.IntegerField(required=False)
    user = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(choices=ReservationStatus.choices, required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
