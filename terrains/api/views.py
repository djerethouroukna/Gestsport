from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from users.api.permissions.user_permissions import IsAdminUser
from terrains.models import Terrain, TerrainType
from terrains.serializers import (
    TerrainSerializer, TerrainListSerializer, TerrainDetailSerializer,
    TerrainCreateSerializer, TerrainUpdateSerializer,
    TerrainAvailabilitySerializer, TerrainSearchSerializer
)

class TerrainViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des terrains"""
    serializer_class = TerrainSerializer
    permission_classes = [permissions.AllowAny]  # Temporairement pour les tests
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['terrain_type', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price_per_hour', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filtrer selon la disponibilité et autres critères"""
        queryset = Terrain.objects.all()
        
        # Filtrer par statut si spécifié
        status = self.request.query_params.get('status')
        if status is not None:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_serializer_class(self):
        """Sélection du sérialiseur selon l'action"""
        if self.action == 'create':
            return TerrainSerializer  # Utiliser le serializer de base pour éviter les erreurs
        elif self.action == 'update' or self.action == 'partial_update':
            return TerrainSerializer  # Utiliser le serializer de base pour éviter les erreurs
        elif self.action == 'list':
            return TerrainListSerializer
        elif self.action == 'retrieve':
            return TerrainDetailSerializer
        return TerrainSerializer
    
    def create(self, request, *args, **kwargs):
        """Créer un terrain avec gestion d'erreur simplifiée"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                self.perform_create(serializer)
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Erreur lors de la création: {e}")
            return Response(
                {"error": f"Erreur lors de la création: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_permissions(self):
        """Permissions selon l'action"""
        # Temporairement plus permissif pour les tests
        return [permissions.AllowAny]
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Vérifier la disponibilité détaillée d'un terrain"""
        terrain = self.get_object()
        serializer = TerrainDetailSerializer(terrain, context={'request': request})
        
        return Response({
            'terrain': serializer.data,
            'availability': serializer.get_availability_status(terrain),
            'upcoming_reservations': serializer.get_upcoming_reservations(terrain)
        })
    
    @action(detail=True, methods=['post'])
    def check_availability(self, request, pk=None):
        """Vérifier la disponibilité pour une période spécifique"""
        terrain = self.get_object()

        # Valider les données via le serializer
        data = {
            'terrain_id': terrain.id,
            'start_time': request.data.get('start_time'),
            'end_time': request.data.get('end_time')
        }
        serializer = TerrainAvailabilitySerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Parser les datetimes (ISO)
        from datetime import datetime
        from django.utils import timezone
        start_iso = serializer.validated_data.get('start_time')
        end_iso = serializer.validated_data.get('end_time')

        try:
            start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
            # Rendre timezone-aware si nécessaire
            if start_dt.tzinfo is None:
                start_dt = timezone.make_aware(start_dt)
            if end_dt.tzinfo is None:
                end_dt = timezone.make_aware(end_dt)
        except Exception as e:
            return Response({'error': 'Format de date/heure invalide'}, status=status.HTTP_400_BAD_REQUEST)

        # Vérifier la disponibilité via le service terrain
        from terrains.utils import TerrainAvailabilityService
        availability = TerrainAvailabilityService.check_period_availability(terrain, start_dt, end_dt)

        return Response({
            'available': availability.get('available', False),
            'reason': availability.get('reason'),
            'conflicts': availability.get('conflicts', []),
            'terrain': TerrainListSerializer(terrain, context={'request': request}).data
        })
    
    @action(detail=False, methods=['get'])
    def available_now(self, request):
        """Lister les terrains disponibles maintenant"""
        from .models import TerrainStatus
        
        now = timezone.now()
        
        # Récupérer tous les terrains avec statut disponible
        available_terrains = Terrain.objects.filter(status=TerrainStatus.AVAILABLE)
        
        # Filtrer ceux qui sont vraiment disponibles maintenant
        truly_available = []
        for terrain in available_terrains:
            # Vérifier si en maintenance
            active_maintenance = terrain.maintenance_periods.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gt=now
            ).exists()
            if active_maintenance:
                continue
            
            # Vérifier horaires d'ouverture
            current_weekday = now.weekday()
            current_time = now.time()
            
            opening_hours = terrain.opening_hours.filter(
                day_of_week=current_weekday,
                is_closed=False
            ).first()
            
            if not opening_hours:
                continue  # Fermé ce jour
            
            if not (opening_hours.opening_time <= current_time <= opening_hours.closing_time):
                continue  # Hors horaires
            
            # Vérifier les réservations en cours
            from reservations.models import Reservation
            current_reservations = Reservation.objects.filter(
                terrain=terrain,
                status__in=['pending', 'confirmed'],
                start_time__lte=now,
                end_time__gt=now
            )
            
            if not current_reservations.exists():
                truly_available.append(terrain)
        
        serializer = TerrainListSerializer(truly_available, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Filtrer les terrains par type"""
        terrain_type = request.query_params.get('type')
        
        if not terrain_type:
            return Response(
                {'error': 'Veuillez spécifier un type de terrain'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Valider que le type existe
        valid_types = [choice[0] for choice in TerrainType.choices]
        if terrain_type not in valid_types:
            return Response(
                {'error': f'Type invalide. Types disponibles: {valid_types}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        terrains = Terrain.objects.filter(terrain_type=terrain_type, status='available')
        serializer = TerrainListSerializer(terrains, many=True, context={'request': request})
        
        return Response({
            'terrain_type': terrain_type,
            'terrain_type_display': dict(TerrainType.choices).get(terrain_type),
            'terrains': serializer.data,
            'count': terrains.count()
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Recherche avancée de terrains"""
        serializer = TerrainSearchSerializer(data=request.GET)
        if serializer.is_valid():
            query = serializer.validated_data
            
            terrains = Terrain.objects.all()
            
            # Filtres
            if query.get('query'):
                terrains = terrains.filter(
                    Q(name__icontains=query['query']) |
                    Q(description__icontains=query['query'])
                )
            
            if query.get('terrain_type'):
                terrains = terrains.filter(terrain_type=query['terrain_type'])
            
            if query.get('min_capacity'):
                terrains = terrains.filter(capacity__gte=query['min_capacity'])
            
            if query.get('max_price'):
                terrains = terrains.filter(price_per_hour__lte=query['max_price'])
            
            if query.get('status') is not None:
                terrains = terrains.filter(status=query['status'])
            
            # Filtrer par disponibilité temporelle
            if query.get('available_from') and query.get('available_to'):
                from reservations.models import Reservation
                available_terrains = []
                
                for terrain in terrains:
                    conflicting_reservations = Reservation.objects.filter(
                        terrain=terrain,
                        status__in=['pending', 'confirmed'],
                        start_time__lt=query['available_to'],
                        end_time__gt=query['available_from']
                    )
                    
                    if not conflicting_reservations.exists():
                        available_terrains.append(terrain)
                
                terrains = available_terrains
            
            # Pagination
            page = self.paginate_queryset(terrains.order_by('name'))
            if page is not None:
                serializer = TerrainListSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = TerrainListSerializer(terrains, many=True, context={'request': request})
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Statistiques sur les terrains (admin uniquement)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Accès refusé'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        total_terrains = Terrain.objects.count()
        available_terrains = Terrain.objects.filter(status='available').count()
        
        # Répartition par type
        type_stats = {}
        for terrain_type, display_name in TerrainType.choices:
            count = Terrain.objects.filter(terrain_type=terrain_type).count()
            type_stats[terrain_type] = {
                'display_name': display_name,
                'count': count,
                'percentage': round((count / total_terrains) * 100, 1) if total_terrains > 0 else 0
            }
        
        # Répartition par statut
        status_stats = {}
        for status_value, display_name in TerrainStatus.choices:
            count = Terrain.objects.filter(status=status_value).count()
            status_stats[status_value] = {
                'display_name': display_name,
                'count': count,
                'percentage': round((count / total_terrains) * 100, 1) if total_terrains > 0 else 0
            }
        
        # Prix moyens par type
        price_stats = {}
        for terrain_type, _ in TerrainType.choices:
            terrains = Terrain.objects.filter(terrain_type=terrain_type)
            if terrains.exists():
                avg_price = terrains.aggregate(models.Avg('price_per_hour'))['price_per_hour__avg']
                price_stats[terrain_type] = round(avg_price, 2) if avg_price else 0
        
        # Note moyenne globale
        avg_rating = Terrain.objects.aggregate(models.Avg('average_rating'))['average_rating__avg']
        
        return Response({
            'total_terrains': total_terrains,
            'available_terrains': available_terrains,
            'unavailable_terrains': total_terrains - available_terrains,
            'availability_rate': round((available_terrains / total_terrains) * 100, 1) if total_terrains > 0 else 0,
            'type_distribution': type_stats,
            'status_distribution': status_stats,
            'average_prices': price_stats,
            'overall_average_rating': round(avg_rating, 2) if avg_rating else 0
        })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_multiple_availability(request):
    """Vérifier la disponibilité de plusieurs terrains pour une période"""
    serializer = TerrainAvailabilitySerializer(data=request.data)
    if serializer.is_valid():
        start_time = serializer.validated_data['start_time']
        end_time = serializer.validated_data['end_time']
        
        # Récupérer tous les terrains avec statut disponible
        available_terrains = Terrain.objects.filter(status='available')
        
        # Vérifier la disponibilité pour chaque terrain
        results = []
        from reservations.models import Reservation
        
        for terrain in available_terrains:
            conflicting_reservations = Reservation.objects.filter(
                terrain=terrain,
                status__in=['pending', 'confirmed'],
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            
            is_available = not conflicting_reservations.exists()
            
            results.append({
                'terrain': TerrainListSerializer(terrain, context={'request': request}).data,
                'available': is_available,
                'conflicts_count': conflicting_reservations.count()
            })
        
        return Response({
            'period': {
                'start_time': start_time,
                'end_time': end_time
            },
            'results': results,
            'available_count': len([r for r in results if r['available']]),
            'total_count': len(results)
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def terrain_types(request):
    """Lister tous les types de terrains disponibles"""
    return Response([
        {
            'value': choice[0],
            'label': choice[1]
        }
        for choice in TerrainType.choices
    ])

# TerrainViewSet public pour AppWorking (sans authentification)
class TerrainPublicViewSet(viewsets.ModelViewSet):
    """
    ViewSet public pour les terrains - accessible sans authentification
    Pour développement et démonstration avec AppWorking
    """
    queryset = Terrain.objects.all().order_by('name')
    serializer_class = TerrainListSerializer
    permission_classes = [permissions.AllowAny]  # Pas d'authentification requise
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TerrainSerializer
        return TerrainListSerializer
    
    def get_queryset(self):
        """Retourne tous les terrains avec filtrage optionnel"""
        queryset = Terrain.objects.all().order_by('name')
        
        # Filtrage par recherche
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Filtrage par statut
        status = self.request.query_params.get('status', None)
        if status and status != 'all':
            queryset = queryset.filter(status=status)
        
        # Filtrage par type
        terrain_type = self.request.query_params.get('terrain_type', None)
        if terrain_type and terrain_type != 'all':
            queryset = queryset.filter(terrain_type=terrain_type)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Retourne la liste des terrains avec pagination"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Format de réponse compatible avec AppWorking
            return self.get_paginated_response({
                'terrains': serializer.data,
                'total': queryset.count()
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'terrains': serializer.data,
            'total': queryset.count()
        })
    
    def create(self, request, *args, **kwargs):
        """Créer un nouveau terrain (public pour AppWorking)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
