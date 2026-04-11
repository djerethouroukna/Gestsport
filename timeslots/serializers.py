# timeslots/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from datetime import datetime, date, time
from decimal import Decimal

from .models import TimeSlot, AvailabilityRule, TimeSlotGeneration, TimeSlotBlock, TimeSlotStatus
from terrains.models import Terrain

User = get_user_model()


class TimeSlotSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les créneaux horaires"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    duration_hours = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()
    can_be_booked = serializers.ReadOnlyField()
    effective_price = serializers.SerializerMethodField()
    reservation_details = serializers.SerializerMethodField()
    
    class Meta:
        model = TimeSlot
        fields = (
            'id', 'terrain', 'terrain_name', 'date', 'start_time', 'end_time',
            'status', 'status_display', 'reservation', 'reservation_details',
            'price_override', 'effective_price', 'is_recurring', 'recurring_pattern',
            'duration_minutes', 'duration_hours', 'is_available', 'can_be_booked',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'reservation', 'duration_minutes', 'duration_hours',
            'is_available', 'can_be_booked', 'created_at', 'updated_at'
        )
    
    def get_effective_price(self, obj):
        """Calcule le prix effectif du créneau"""
        from .services import TimeSlotService
        price = TimeSlotService.get_timeslot_price(obj)
        return float(price)
    
    def get_reservation_details(self, obj):
        """Récupère les détails de la réservation associée"""
        if obj.reservation:
            return {
                'id': obj.reservation.id,
                'user_name': obj.reservation.user.get_full_name() or obj.reservation.user.username,
                'start_time': obj.reservation.start_time,
                'end_time': obj.reservation.end_time,
                'status': obj.reservation.status
            }
        return None


class TimeSlotCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un créneau horaire"""
    
    class Meta:
        model = TimeSlot
        fields = (
            'terrain', 'date', 'start_time', 'end_time', 'price_override'
        )
    
    def validate(self, attrs):
        """Valide la cohérence des données"""
        start_time = attrs['start_time']
        end_time = attrs['end_time']
        
        if end_time <= start_time:
            raise serializers.ValidationError("L'heure de fin doit être après l'heure de début")
        
        # Vérifier que le créneau n'existe pas déjà
        existing = TimeSlot.objects.filter(
            terrain=attrs['terrain'],
            date=attrs['date'],
            start_time=start_time,
            end_time=end_time
        ).first()
        
        if existing:
            raise serializers.ValidationError("Ce créneau horaire existe déjà")
        
        return attrs


class TimeSlotAvailabilitySerializer(serializers.Serializer):
    """Sérialiseur pour vérifier la disponibilité"""
    terrain_id = serializers.IntegerField()
    date = serializers.DateField()
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    
    def validate_terrain_id(self, value):
        """Vérifie que le terrain existe"""
        try:
            Terrain.objects.get(id=value)
            return value
        except Terrain.DoesNotExist:
            raise serializers.ValidationError("Terrain introuvable")


class TimeSlotBookingSerializer(serializers.Serializer):
    """Sérialiseur pour réserver un créneau"""
    timeslot_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_timeslot_id(self, value):
        """Vérifie que le créneau existe et est disponible"""
        try:
            timeslot = TimeSlot.objects.get(id=value)
            if not timeslot.can_be_booked:
                raise serializers.ValidationError("Ce créneau n'est pas disponible")
            return value
        except TimeSlot.DoesNotExist:
            raise serializers.ValidationError("Créneau introuvable")


class AvailabilityRuleSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les règles de disponibilité"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    
    class Meta:
        model = AvailabilityRule
        fields = (
            'id', 'terrain', 'terrain_name', 'rule_type', 'rule_type_display',
            'name', 'description', 'priority', 'start_date', 'end_date',
            'start_time', 'end_time', 'monday', 'tuesday', 'wednesday',
            'thursday', 'friday', 'saturday', 'sunday',
            'price_multiplier', 'price_override', 'is_active',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class AvailabilityRuleCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer une règle de disponibilité"""
    
    class Meta:
        model = AvailabilityRule
        fields = (
            'terrain', 'rule_type', 'name', 'description', 'priority',
            'start_date', 'end_date', 'start_time', 'end_time',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday', 'price_multiplier', 'price_override'
        )
    
    def validate(self, attrs):
        """Valide la cohérence des données"""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("La date de fin doit être après la date de début")
        
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError("L'heure de fin doit être après l'heure de début")
        
        return attrs


class TimeSlotGenerationSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les générations de créneaux"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = TimeSlotGeneration
        fields = (
            'id', 'terrain', 'terrain_name', 'start_date', 'end_date',
            'slot_duration', 'slots_generated', 'generation_method',
            'created_by', 'created_by_name', 'created_at'
        )
        read_only_fields = (
            'id', 'slots_generated', 'generation_method',
            'created_by', 'created_at'
        )


class TimeSlotGenerationCreateSerializer(serializers.Serializer):
    """Sérialiseur pour créer une génération de créneaux"""
    terrain_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    slot_duration = serializers.IntegerField(min_value=15, max_value=480)
    
    def validate_terrain_id(self, value):
        """Vérifie que le terrain existe"""
        try:
            Terrain.objects.get(id=value)
            return value
        except Terrain.DoesNotExist:
            raise serializers.ValidationError("Terrain introuvable")
    
    def validate(self, attrs):
        """Valide la cohérence des dates"""
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError("La date de fin doit être après la date de début")
        
        # Limiter la période à 1 an
        max_date = attrs['start_date'].replace(year=attrs['start_date'].year + 1)
        if attrs['end_date'] > max_date:
            raise serializers.ValidationError("La période ne peut pas dépasser 1 an")
        
        return attrs


class TimeSlotBlockSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les blocages de créneaux"""
    terrain_name = serializers.CharField(source='terrain.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = TimeSlotBlock
        fields = (
            'id', 'terrain', 'terrain_name', 'start_datetime', 'end_datetime',
            'reason', 'is_maintenance', 'created_by', 'created_by_name',
            'created_at'
        )
        read_only_fields = (
            'id', 'created_by', 'created_at'
        )


class TimeSlotBlockCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un blocage de créneaux"""
    
    class Meta:
        model = TimeSlotBlock
        fields = (
            'terrain', 'start_datetime', 'end_datetime', 'reason', 'is_maintenance'
        )
    
    def validate(self, attrs):
        """Valide la cohérence des données"""
        if attrs['end_datetime'] <= attrs['start_datetime']:
            raise serializers.ValidationError("La date de fin doit être après la date de début")
        
        # Limiter la durée du blocage à 7 jours
        max_duration = timedelta(days=7)
        if attrs['end_datetime'] - attrs['start_datetime'] > max_duration:
            raise serializers.ValidationError("La durée du blocage ne peut pas dépasser 7 jours")
        
        return attrs


class DailyAvailabilitySerializer(serializers.Serializer):
    """Sérialiseur pour la disponibilité quotidienne"""
    date = serializers.DateField()
    terrain = serializers.CharField()
    total_slots = serializers.IntegerField()
    available_slots = serializers.IntegerField()
    booked_slots = serializers.IntegerField()
    blocked_slots = serializers.IntegerField()
    availability_rate = serializers.FloatField()
    timeslots = TimeSlotSerializer(many=True)


class WeeklyAvailabilitySerializer(serializers.Serializer):
    """Sérialiseur pour la disponibilité hebdomadaire"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    terrain = serializers.CharField()
    daily_data = serializers.DictField(child=DailyAvailabilitySerializer())


class TimeSlotSearchSerializer(serializers.Serializer):
    """Sérialiseur pour la recherche de créneaux"""
    terrain_id = serializers.IntegerField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    min_duration = serializers.IntegerField(required=False, min_value=15)
    max_price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    status = serializers.ChoiceField(
        choices=TimeSlotStatus.choices,
        required=False
    )
    
    def validate(self, attrs):
        """Valide la cohérence des paramètres"""
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("La date de fin doit être après la date de début")
        
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError("L'heure de fin doit être après l'heure de début")
        
        return attrs


class TimeSlotPriceUpdateSerializer(serializers.Serializer):
    """Sérialiseur pour mettre à jour le prix d'un créneau"""
    timeslot_id = serializers.UUIDField()
    price_override = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate_timeslot_id(self, value):
        """Vérifie que le créneau existe"""
        try:
            TimeSlot.objects.get(id=value)
            return value
        except TimeSlot.DoesNotExist:
            raise serializers.ValidationError("Créneau introuvable")
    
    def validate_price_override(self, value):
        """Valide le prix"""
        if value <= 0:
            raise serializers.ValidationError("Le prix doit être positif")
        return value
