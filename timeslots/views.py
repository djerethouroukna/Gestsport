# timeslots/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from datetime import datetime, date, time, timedelta

from .models import TimeSlot, AvailabilityRule, TimeSlotGeneration, TimeSlotBlock, TimeSlotStatus
from .serializers import (
    TimeSlotSerializer, TimeSlotCreateSerializer, TimeSlotAvailabilitySerializer,
    TimeSlotBookingSerializer, AvailabilityRuleSerializer, AvailabilityRuleCreateSerializer,
    TimeSlotGenerationSerializer, TimeSlotGenerationCreateSerializer,
    TimeSlotBlockSerializer, TimeSlotBlockCreateSerializer,
    DailyAvailabilitySerializer, WeeklyAvailabilitySerializer,
    TimeSlotSearchSerializer, TimeSlotPriceUpdateSerializer
)
from .services import TimeSlotService, AvailabilityRuleService, TimeSlotBulkService

User = get_user_model()


class TimeSlotPagination(PageNumberPagination):
    """Pagination pour les créneaux horaires"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class TimeSlotViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des créneaux horaires"""
    serializer_class = TimeSlotSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TimeSlotPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['terrain', 'status', 'date']
    search_fields = ['terrain__name', 'reservation__user__first_name', 'reservation__user__last_name']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['date', 'start_time']
    
    def get_queryset(self):
        """Filtrer selon le rôle de l'utilisateur"""
        user = self.request.user
        
        if user.role == 'admin':
            return TimeSlot.objects.all()
        elif user.role == 'coach':
            # Les coachs voient tous les créneaux
            return TimeSlot.objects.all()
        else:  # player
            # Les joueurs voient tous les créneaux (consultation)
            return TimeSlot.objects.all()
    
    def get_serializer_class(self):
        """Utiliser le bon sérialiseur selon l'action"""
        if self.action == 'create':
            return TimeSlotCreateSerializer
        return TimeSlotSerializer
    
    @action(detail=False, methods=['post'], permission_classes=[])
    def check_availability(self, request):
        """Vérifier la disponibilité pour une période (publique)"""
        serializer = TimeSlotAvailabilitySerializer(data=request.data)
        
        if serializer.is_valid():
            terrain_id = serializer.validated_data['terrain_id']
            target_date = serializer.validated_data['date']
            start_time = serializer.validated_data.get('start_time')
            end_time = serializer.validated_data.get('end_time')
            
            from terrains.models import Terrain
            terrain = Terrain.objects.get(id=terrain_id)
            
            if start_time and end_time:
                start_datetime = datetime.combine(target_date, start_time)
                end_datetime = datetime.combine(target_date, end_time)
                
                is_available, conflicting_slots = TimeSlotService.check_availability(
                    terrain, start_datetime, end_datetime
                )
                
                return Response({
                    'success': True,
                    'is_available': is_available,
                    'conflicting_slots': TimeSlotSerializer(conflicting_slots, many=True).data
                })
            else:
                available_slots = TimeSlotService.get_available_timeslots(
                    terrain, target_date, start_time, end_time
                )
                
                return Response({
                    'success': True,
                    'available_slots': TimeSlotSerializer(available_slots, many=True).data
                })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        """Réserver un créneau horaire"""
        try:
            timeslot = self.get_object()
            
            if not timeslot.can_be_booked:
                return Response({
                    'success': False,
                    'message': 'Ce créneau n\'est pas disponible'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Créer une réservation
            from reservations.models import Reservation
            
            start_datetime = datetime.combine(timeslot.date, timeslot.start_time)
            end_datetime = datetime.combine(timeslot.date, timeslot.end_time)
            
            reservation = Reservation.objects.create(
                user=request.user,
                terrain=timeslot.terrain,
                start_time=start_datetime,
                end_time=end_datetime,
                status='pending'
            )
            
            # Réserver le créneau
            success = TimeSlotService.book_timeslot(timeslot, reservation)
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Créneau réservé avec succès',
                    'reservation_id': reservation.id,
                    'timeslot': TimeSlotSerializer(timeslot).data
                })
            else:
                reservation.delete()
                return Response({
                    'success': False,
                    'message': 'Impossible de réserver ce créneau'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Libérer un créneau horaire (admin/coach uniquement)"""
        if request.user.role not in ['admin', 'coach']:
            return Response({
                'success': False,
                'message': 'Permission refusée'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            timeslot = self.get_object()
            
            success = TimeSlotService.release_timeslot(timeslot)
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Créneau libéré avec succès',
                    'timeslot': TimeSlotSerializer(timeslot).data
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Impossible de libérer ce créneau'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """Mettre à jour le prix d'un créneau"""
        if request.user.role not in ['admin', 'coach']:
            return Response({
                'success': False,
                'message': 'Permission refusée'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TimeSlotPriceUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                timeslot = self.get_object()
                timeslot.price_override = serializer.validated_data['price_override']
                timeslot.save()
                
                return Response({
                    'success': True,
                    'message': 'Prix mis à jour avec succès',
                    'timeslot': TimeSlotSerializer(timeslot).data
                })
            except Exception as e:
                return Response({
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def daily_availability(self, request):
        """Récupérer la disponibilité quotidienne"""
        terrain_id = request.GET.get('terrain_id')
        target_date = request.GET.get('date')
        
        if not terrain_id or not target_date:
            return Response({
                'success': False,
                'message': 'terrain_id et date sont requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from terrains.models import Terrain
            terrain = Terrain.objects.get(id=terrain_id)
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            availability = TimeSlotService.get_daily_availability(terrain, target_date)
            
            return Response({
                'success': True,
                'availability': availability
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def weekly_availability(self, request):
        """Récupérer la disponibilité hebdomadaire"""
        terrain_id = request.GET.get('terrain_id')
        start_date = request.GET.get('start_date')
        
        if not terrain_id or not start_date:
            return Response({
                'success': False,
                'message': 'terrain_id et start_date sont requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from terrains.models import Terrain
            terrain = Terrain.objects.get(id=terrain_id)
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            weekly_data = TimeSlotService.get_weekly_availability(terrain, start_date)
            
            return Response({
                'success': True,
                'weekly_availability': weekly_data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AvailabilityRuleViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des règles de disponibilité"""
    serializer_class = AvailabilityRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['terrain', 'rule_type', 'is_active']
    search_fields = ['name', 'description', 'terrain__name']
    ordering_fields = ['priority', 'created_at']
    ordering = ['-priority', 'created_at']
    
    def get_queryset(self):
        """Filtrer selon le rôle de l'utilisateur"""
        user = self.request.user
        
        if user.role == 'admin':
            return AvailabilityRule.objects.all()
        elif user.role == 'coach':
            # Les coachs voient toutes les règles
            return AvailabilityRule.objects.all()
        else:  # player
            # Les joueurs voient uniquement les règles actives
            return AvailabilityRule.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        """Utiliser le bon sérialiseur selon l'action"""
        if self.action == 'create':
            return AvailabilityRuleCreateSerializer
        return AvailabilityRuleSerializer
    
    @action(detail=False, methods=['post'])
    def create_weekend_premium(self, request):
        """Créer une règle de majoration week-end"""
        if request.user.role not in ['admin', 'coach']:
            return Response({
                'success': False,
                'message': 'Permission refusée'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            terrain_id = request.data.get('terrain_id')
            multiplier = request.data.get('multiplier', 1.5)
            
            from terrains.models import Terrain
            terrain = Terrain.objects.get(id=terrain_id)
            
            rule = AvailabilityRuleService.create_weekend_premium_rule(
                terrain=terrain,
                multiplier=multiplier
            )
            
            return Response({
                'success': True,
                'message': 'Règle week-end créée avec succès',
                'rule': AvailabilityRuleSerializer(rule).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def create_evening_premium(self, request):
        """Créer une règle de majoration soirée"""
        if request.user.role not in ['admin', 'coach']:
            return Response({
                'success': False,
                'message': 'Permission refusée'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            terrain_id = request.data.get('terrain_id')
            start_time = request.data.get('start_time', '18:00')
            multiplier = request.data.get('multiplier', 1.3)
            
            from terrains.models import Terrain
            terrain = Terrain.objects.get(id=terrain_id)
            
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            
            rule = AvailabilityRuleService.create_evening_premium_rule(
                terrain=terrain,
                start_time=start_time_obj,
                multiplier=multiplier
            )
            
            return Response({
                'success': True,
                'message': 'Règle soirée créée avec succès',
                'rule': AvailabilityRuleSerializer(rule).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TimeSlotGenerationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour l'historique des générations de créneaux"""
    serializer_class = TimeSlotGenerationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TimeSlotPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['terrain', 'generation_method']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrer selon le rôle de l'utilisateur"""
        user = self.request.user
        
        if user.role == 'admin':
            return TimeSlotGeneration.objects.all()
        elif user.role == 'coach':
            # Les coachs voient toutes les générations
            return TimeSlotGeneration.objects.all()
        else:  # player
            # Les joueurs ne voient pas les générations
            return TimeSlotGeneration.objects.none()
    
    @action(detail=False, methods=['post'])
    def generate_range(self, request):
        """Générer des créneaux pour une période"""
        if request.user.role not in ['admin', 'coach']:
            return Response({
                'success': False,
                'message': 'Permission refusée'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TimeSlotGenerationCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                from terrains.models import Terrain
                terrain = Terrain.objects.get(
                    id=serializer.validated_data['terrain_id']
                )
                
                result = TimeSlotService.generate_range_timeslots(
                    terrain=terrain,
                    start_date=serializer.validated_data['start_date'],
                    end_date=serializer.validated_data['end_date'],
                    duration_minutes=serializer.validated_data['slot_duration'],
                    created_by=request.user
                )
                
                return Response({
                    'success': True,
                    'message': 'Créneaux générés avec succès',
                    'result': result
                })
                
            except Exception as e:
                return Response({
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def regenerate_month(self, request):
        """Régénérer les créneaux pour un mois"""
        if request.user.role not in ['admin', 'coach']:
            return Response({
                'success': False,
                'message': 'Permission refusée'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            terrain_id = request.data.get('terrain_id')
            year = request.data.get('year')
            month = request.data.get('month')
            
            from terrains.models import Terrain
            terrain = Terrain.objects.get(id=terrain_id)
            
            result = TimeSlotBulkService.regenerate_month_timeslots(
                terrain=terrain,
                year=year,
                month=month,
                created_by=request.user
            )
            
            return Response({
                'success': True,
                'message': 'Mois régénéré avec succès',
                'result': result
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TimeSlotBlockViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des blocages de créneaux"""
    serializer_class = TimeSlotBlockSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TimeSlotPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['terrain', 'is_maintenance']
    search_fields = ['reason', 'terrain__name']
    ordering_fields = ['created_at', 'start_datetime']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrer selon le rôle de l'utilisateur"""
        user = self.request.user
        
        if user.role == 'admin':
            return TimeSlotBlock.objects.all()
        elif user.role == 'coach':
            # Les coachs voient tous les blocages
            return TimeSlotBlock.objects.all()
        else:  # player
            # Les joueurs voient uniquement les blocages actifs
            return TimeSlotBlock.filter(
                start_datetime__gte=timezone.now()
            )
    
    def get_serializer_class(self):
        """Utiliser le bon sérialiseur selon l'action"""
        if self.action == 'create':
            return TimeSlotBlockCreateSerializer
        return TimeSlotBlockSerializer
    
    def perform_create(self, serializer):
        """Assigner l'utilisateur lors de la création"""
        serializer.save(created_by=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_timeslots(request):
    """Rechercher des créneaux horaires"""
    serializer = TimeSlotSearchSerializer(data=request.query_params)
    
    if serializer.is_valid():
        try:
            queryset = TimeSlot.objects.all()
            
            # Appliquer les filtres
            terrain_id = serializer.validated_data.get('terrain_id')
            if terrain_id:
                queryset = queryset.filter(terrain_id=terrain_id)
            
            start_date = serializer.validated_data.get('start_date')
            if start_date:
                queryset = queryset.filter(date__gte=start_date)
            
            end_date = serializer.validated_data.get('end_date')
            if end_date:
                queryset = queryset.filter(date__lte=end_date)
            
            start_time = serializer.validated_data.get('start_time')
            if start_time:
                queryset = queryset.filter(start_time__gte=start_time)
            
            end_time = serializer.validated_data.get('end_time')
            if end_time:
                queryset = queryset.filter(end_time__lte=end_time)
            
            status = serializer.validated_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Pagination
            page_size = int(request.GET.get('page_size', 50))
            page = int(request.GET.get('page', 1))
            
            start = (page - 1) * page_size
            end = start + page_size
            
            timeslots_page = queryset[start:end]
            
            return Response({
                'success': True,
                'timeslots': TimeSlotSerializer(timeslots_page, many=True).data,
                'pagination': {
                    'current_page': page,
                    'total_pages': (queryset.count() + page_size - 1) // page_size,
                    'total_count': queryset.count(),
                    'page_size': page_size
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_block_timeslots(request):
    """Blocage massif de créneaux"""
    if request.user.role not in ['admin', 'coach']:
        return Response({
            'success': False,
            'message': 'Permission refusée'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        terrain_id = request.data.get('terrain_id')
        start_datetime = datetime.fromisoformat(request.data.get('start_datetime'))
        end_datetime = datetime.fromisoformat(request.data.get('end_datetime'))
        reason = request.data.get('reason')
        is_maintenance = request.data.get('is_maintenance', False)
        
        from terrains.models import Terrain
        terrain = Terrain.objects.get(id=terrain_id)
        
        blocked_count = TimeSlotService.block_timeslots(
            terrain=terrain,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            reason=reason,
            created_by=request.user,
            is_maintenance=is_maintenance
        )
        
        return Response({
            'success': True,
            'message': f'{blocked_count} créneaux bloqués avec succès',
            'blocked_count': blocked_count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
