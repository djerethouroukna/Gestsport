from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Terrain, TerrainType, TerrainStatus, Equipment, TerrainPhoto, TerrainEquipment, OpeningHours, MaintenancePeriod, Review

class TerrainSerializer(serializers.ModelSerializer):
    """Sérialiseur principal pour les terrains"""
    terrain_type_display = serializers.CharField(source='get_terrain_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    primary_photo_url = serializers.SerializerMethodField()
    photos_count = serializers.SerializerMethodField()
    is_available_now = serializers.SerializerMethodField()
    
    class Meta:
        model = Terrain
        fields = (
            'id', 'name', 'description', 'terrain_type', 'terrain_type_display',
            'capacity', 'price_per_hour', 'status', 'status_display',
            'average_rating', 'primary_photo_url', 'photos_count',
            'is_available_now', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_primary_photo_url(self, obj):
        """Retourne l'URL de la photo principale"""
        primary_photo = obj.photos.filter(is_primary=True).first()
        if primary_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_photo.image.url)
            return primary_photo.image.url
        # Fallback vers première photo disponible
        first_photo = obj.photos.first()
        if first_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_photo.image.url)
            return first_photo.image.url
        return None
    
    def get_photos_count(self, obj):
        """Retourne le nombre de photos"""
        return obj.photos.count()
    
    def get_equipments(self, obj):
        """Retourne les équipements du terrain"""
        return [equipment.name for equipment in obj.equipments.all()]
    
    def get_opening_hours(self, obj):
        """Retourne les horaires d'ouverture du terrain"""
        opening_hours = obj.opening_hours.all()
        return [
            {
                'day_of_week': opening_hour.day_of_week,
                'opening_time': opening_hour.opening_time,
                'closing_time': opening_hour.closing_time,
                'is_closed': opening_hour.is_closed
            }
            for opening_hour in opening_hours
        ]
    
    def get_maintenance_status(self, obj):
        """Retourne le statut de maintenance du terrain"""
        active_maintenance = obj.maintenance_periods.filter(is_active=True).first()
        if active_maintenance:
            return {
                'is_active': True,
                'start_date': active_maintenance.start_date,
                'end_date': active_maintenance.end_date,
                'reason': active_maintenance.reason
            }
        return {'is_active': False}
    
    def get_reviews_summary(self, obj):
        """Retourne un résumé des avis du terrain"""
        reviews = obj.reviews.all()
        return {
            'average_rating': obj.average_rating,
            'total_reviews': reviews.count(),
            'latest_reviews': [
                {
                    'id': review.id,
                    'user_name': review.user.get_full_name(),
                    'rating': review.rating,
                    'comment': review.comment,
                    'created_at': review.created_at
                }
                for review in reviews.order_by('-created_at')[:5]
            ]
        }
    
    def get_is_available_now(self, obj):
        """Vérifie si le terrain est disponible maintenant"""
        if obj.status != TerrainStatus.AVAILABLE:
            return False
        
        now = timezone.now()
        
        # Vérifier si en maintenance
        active_maintenance = obj.maintenance_periods.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gt=now
        ).exists()
        if active_maintenance:
            return False
        
        # Vérifier horaires d'ouverture
        current_weekday = now.weekday()
        current_time = now.time()
        
        opening_hours = obj.opening_hours.filter(
            day_of_week=current_weekday,
            is_closed=False
        ).first()
        
        if not opening_hours:
            return False  # Fermé ce jour
        
        if not (opening_hours.opening_time <= current_time <= opening_hours.closing_time):
            return False  # Hors horaires
        
        # Vérifier les réservations en cours
        from reservations.models import Reservation
        current_reservations = Reservation.objects.filter(
            terrain=obj,
            status__in=['pending', 'confirmed'],
            start_time__lte=now,
            end_time__gt=now
        )
        
        return not current_reservations.exists()

class TerrainListSerializer(serializers.ModelSerializer):
    """Sérialiseur pour lister les terrains (moins de détails)"""
    terrain_type_display = serializers.CharField(source='get_terrain_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    primary_photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Terrain
        fields = (
            'id', 'name', 'terrain_type', 'terrain_type_display',
            'capacity', 'price_per_hour', 'status', 'status_display',
            'average_rating', 'primary_photo_url'
        )
    
    def get_primary_photo_url(self, obj):
        """Retourne l'URL de la photo principale"""
        primary_photo = obj.photos.filter(is_primary=True).first()
        if primary_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_photo.image.url)
            return primary_photo.image.url
        first_photo = obj.photos.first()
        if first_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_photo.image.url)
            return first_photo.image.url
        return None

class TerrainDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les détails complets d'un terrain"""
    terrain_type_display = serializers.CharField(source='get_terrain_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    primary_photo_url = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
    equipments = serializers.SerializerMethodField()
    opening_hours = serializers.SerializerMethodField()
    upcoming_reservations = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()
    reviews_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Terrain
        fields = (
            'id', 'name', 'description', 'terrain_type', 'terrain_type_display',
            'capacity', 'price_per_hour', 'status', 'status_display',
            'average_rating', 'primary_photo_url', 'photos', 'equipments',
            'opening_hours', 'upcoming_reservations', 'availability_status',
            'reviews_summary', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_primary_photo_url(self, obj):
        """Retourne l'URL de la photo principale"""
        primary_photo = obj.photos.filter(is_primary=True).first()
        if primary_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_photo.image.url)
            return primary_photo.image.url
        first_photo = obj.photos.first()
        if first_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_photo.image.url)
            return first_photo.image.url
        return None
    
    def get_photos(self, obj):
        """Retourne toutes les photos"""
        photos = obj.photos.all().order_by('order')
        request = self.context.get('request')
        result = []
        for photo in photos:
            photo_data = {
                'id': photo.id,
                'caption': photo.caption,
                'order': photo.order,
                'is_primary': photo.is_primary
            }
            if request:
                photo_data['url'] = request.build_absolute_uri(photo.image.url)
            else:
                photo_data['url'] = photo.image.url
            result.append(photo_data)
        return result
    
    def get_equipments(self, obj):
        """Retourne les équipements du terrain"""
        equipments = obj.terrain_equipments.all()
        return [
            {
                'id': te.id,
                'equipment': {
                    'id': te.equipment.id,
                    'name': te.equipment.name,
                    'description': te.equipment.description,
                    'icon': te.equipment.icon
                },
                'quantity': te.quantity,
                'condition': te.condition,
                'condition_display': te.get_condition_display()
            }
            for te in equipments
        ]
    
    def get_opening_hours(self, obj):
        """Retourne les horaires d'ouverture"""
        hours = obj.opening_hours.all().order_by('day_of_week')
        return [
            {
                'day_of_week': h.day_of_week,
                'day_name': dict(OpeningHours.WEEKDAYS).get(h.day_of_week),
                'opening_time': h.opening_time,
                'closing_time': h.closing_time,
                'is_closed': h.is_closed
            }
            for h in hours
        ]
    
    def get_upcoming_reservations(self, obj):
        """Récupère les réservations à venir pour ce terrain"""
        from reservations.models import Reservation
        
        upcoming = Reservation.objects.filter(
            terrain=obj,
            status__in=['pending', 'confirmed'],
            start_time__gt=timezone.now()
        ).order_by('start_time')[:5]
        
        return [
            {
                'id': res.id,
                'user_name': res.user.get_full_name(),
                'start_time': res.start_time,
                'end_time': res.end_time,
                'status': res.status
            }
            for res in upcoming
        ]
    
    def get_availability_status(self, obj):
        """Statut détaillé de disponibilité"""
        if obj.status != TerrainStatus.AVAILABLE:
            return {
                'status': 'unavailable',
                'message': f'Terrain {obj.get_status_display().lower()}'
            }
        
        now = timezone.now()
        
        # Vérifier maintenance
        active_maintenance = obj.maintenance_periods.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gt=now
        ).first()
        if active_maintenance:
            return {
                'status': 'maintenance',
                'message': 'Terrain en maintenance',
                'reason': active_maintenance.reason,
                'available_at': active_maintenance.end_date
            }
        
        # Vérifier horaires
        current_weekday = now.weekday()
        current_time = now.time()
        
        opening_hours = obj.opening_hours.filter(
            day_of_week=current_weekday,
            is_closed=False
        ).first()
        
        if not opening_hours:
            return {
                'status': 'closed_today',
                'message': 'Terrain fermé aujourd\'hui'
            }
        
        if current_time < opening_hours.opening_time:
            return {
                'status': 'not_open_yet',
                'message': 'Pas encore ouvert',
                'opens_at': opening_hours.opening_time
            }
        
        if current_time > opening_hours.closing_time:
            return {
                'status': 'closed_for_today',
                'message': 'Fermé pour aujourd\'hui'
            }
        
        # Vérifier réservation en cours
        from reservations.models import Reservation
        current_reservations = Reservation.objects.filter(
            terrain=obj,
            status__in=['pending', 'confirmed'],
            start_time__lte=now,
            end_time__gt=now
        ).first()
        
        if current_reservations:
            return {
                'status': 'occupied',
                'message': 'Terrain actuellement occupé',
                'available_at': current_reservations.end_time
            }
        
        # Prochaine réservation
        next_reservation = Reservation.objects.filter(
            terrain=obj,
            status__in=['pending', 'confirmed'],
            start_time__gt=now
        ).order_by('start_time').first()
        
        if next_reservation:
            return {
                'status': 'available',
                'message': 'Disponible maintenant',
                'next_reservation': next_reservation.start_time
            }
        
        return {
            'status': 'fully_available',
            'message': 'Aucune réservation prévue aujourd\'hui'
        }
    
    def get_reviews_summary(self, obj):
        """Résumé des avis"""
        approved_reviews = obj.reviews.filter(is_approved=True)
        total_reviews = approved_reviews.count()
        
        if total_reviews == 0:
            return {
                'total_reviews': 0,
                'average_rating': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        # Distribution des notes
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for review in approved_reviews:
            rating_dist[review.rating] += 1
        
        return {
            'total_reviews': total_reviews,
            'average_rating': obj.average_rating,
            'rating_distribution': rating_dist
        }

class TerrainCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un terrain (admin uniquement)"""
    
    class Meta:
        model = Terrain
        fields = (
            'name', 'description', 'terrain_type', 'capacity',
            'price_per_hour', 'status'
        )
    
    def validate_price_per_hour(self, value):
        """Valider que le prix est positif"""
        if value <= 0:
            raise ValidationError("Le prix par heure doit être positif.")
        return value
    
    def validate_capacity(self, value):
        """Valider que la capacité est positive"""
        if value <= 0:
            raise ValidationError("La capacité doit être positive.")
        return value

class TerrainUpdateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour mettre à jour un terrain (admin uniquement)"""
    
    class Meta:
        model = Terrain
        fields = (
            'name', 'description', 'terrain_type', 'capacity',
            'price_per_hour', 'status'
        )
    
    def validate_price_per_hour(self, value):
        if value <= 0:
            raise ValidationError("Le prix par heure doit être positif.")
        return value
    
    def validate_capacity(self, value):
        if value <= 0:
            raise ValidationError("La capacité doit être positive.")
        return value

class TerrainAvailabilitySerializer(serializers.Serializer):
    """Sérialiseur pour vérifier la disponibilité d'un terrain"""
    terrain_id = serializers.IntegerField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    
    def validate(self, attrs):
        """Valider la disponibilité pour la période demandée"""
        terrain_id = attrs['terrain_id']
        start_time = attrs['start_time']
        end_time = attrs['end_time']
        
        # Vérifier que la date de fin est après la date de début
        if end_time <= start_time:
            raise ValidationError("La date de fin doit être après la date de début.")
        
        # Vérifier que la période n'est pas dans le passé
        if start_time < timezone.now():
            raise ValidationError("Impossible de réserver pour une date passée.")
        
        # Vérifier que le terrain existe et est disponible
        try:
            from .models import Terrain, TerrainStatus
            terrain = Terrain.objects.get(id=terrain_id)
            if terrain.status != TerrainStatus.AVAILABLE:
                raise ValidationError("Ce terrain n'est pas disponible.")
        except Terrain.DoesNotExist:
            raise ValidationError("Terrain non trouvé.")
        
        # Vérifier les conflits de réservation
        from reservations.models import Reservation
        conflicting_reservations = Reservation.objects.filter(
            terrain_id=terrain_id,
            status__in=['pending', 'confirmed'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if conflicting_reservations.exists():
            raise ValidationError("Ce terrain n'est pas disponible pour cette période.")
        
        return attrs

class TerrainSearchSerializer(serializers.Serializer):
    """Sérialiseur pour la recherche de terrains"""
    query = serializers.CharField(required=False, allow_blank=True)
    terrain_type = serializers.ChoiceField(choices=TerrainType.choices, required=False)
    status = serializers.ChoiceField(choices=TerrainStatus.choices, required=False)
    min_capacity = serializers.IntegerField(required=False, min_value=1)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    available_from = serializers.DateTimeField(required=False)
    available_to = serializers.DateTimeField(required=False)
