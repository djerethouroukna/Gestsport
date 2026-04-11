from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from users.api.permissions.user_permissions import (
    CanCreateActivity, CanJoinActivity, IsOwnerOrAdmin, IsAdminOrCoach
)
from activities.models import Activity, ActivityStatus
from activities.serializers import ActivitySerializer

# Permission personnalisée pour admin uniquement
class IsAdminOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

User = get_user_model()

class ActivityViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des activités"""
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'activity_type', 'terrain', 'coach']
    search_fields = ['title', 'description', 'terrain__name']
    ordering_fields = ['start_time', 'created_at']
    
    def get_queryset(self):
        """Filtrer les activités selon le rôle de l'utilisateur"""
        user = self.request.user
        
        if user.role == 'admin':
            return Activity.objects.all()
        elif user.role == 'coach':
            # Les coachs voient toutes les activités + celles qu'ils créent
            return Activity.objects.all()
        else:  # player
            # Les joueurs voient toutes les activités confirmées
            return Activity.objects.filter(status=ActivityStatus.CONFIRMED)
    
    def get_permissions(self):
        """Permissions selon l'action"""
        if self.action == 'create':
            return [CanCreateActivity()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        elif self.action == 'join':
            return [CanJoinActivity()]
        elif self.action == 'confirm':
            return [IsAdminOnly()]
        elif self.action == 'cancel':
            return [IsOwnerOrAdmin()]
        elif self.action == 'reactivate':
            return [IsAdminOnly()]
        else:  # list, retrieve
            return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        """Assigner le coach lors de la création"""
        activity = serializer.save(coach=self.request.user)
        
        # Notification automatique aux admins
        from notifications.utils import NotificationService
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        admins = User.objects.filter(role='admin')
        
        for admin in admins:
            NotificationService.create_notification(
                recipient=admin,
                title="Nouvelle activité à valider",
                message=f"Nouvelle activité '{activity.title}' créée par {activity.coach.get_full_name()} pour le {activity.start_time.strftime('%d/%m/%Y à %H:%M')}.",
                notification_type='activity_reminder',
                content_object=activity
            )
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """S'inscrire à une activité"""
        activity = self.get_object()
        user = request.user
        
        # Vérifier si l'utilisateur peut s'inscrire
        if activity.status != ActivityStatus.CONFIRMED:
            return Response(
                {'error': 'Impossible de s\'inscrire à cette activité'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier si l'utilisateur n'est pas déjà inscrit
        if activity.participants.filter(id=user.id).exists():
            return Response(
                {'error': 'Vous êtes déjà inscrit à cette activité'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier le nombre maximum de participants
        if activity.participants.count() >= activity.max_participants:
            return Response(
                {'error': 'Cette activité est complète'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ajouter l'utilisateur aux participants
        activity.participants.add(user)
        
        # Notification automatique
        from notifications.utils import NotificationService
        NotificationService.create_notification(
            recipient=user,
            title=f"Inscription à {activity.title}",
            message=f"Vous êtes maintenant inscrit à l'activité '{activity.title}' le {activity.start_time.strftime('%d/%m/%Y à %H:%M')}.",
            notification_type='activity_reminder',
            content_object=activity
        )
        
        # Notifier le coach
        NotificationService.create_notification(
            recipient=activity.coach,
            title=f"Nouveau participant à {activity.title}",
            message=f"{user.get_full_name()} s'est inscrit à votre activité '{activity.title}'.",
            notification_type='system_message',
            content_object=activity
        )
        
        return Response({
            'message': 'Inscription réussie',
            'participants_count': activity.participants.count()
        })
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Se désinscrire d'une activité"""
        activity = self.get_object()
        user = request.user
        
        # Vérifier si l'utilisateur est inscrit
        if not activity.participants.filter(id=user.id).exists():
            return Response(
                {'error': 'Vous n\'êtes pas inscrit à cette activité'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Retirer l'utilisateur des participants
        activity.participants.remove(user)
        
        # Notification automatique
        from notifications.utils import NotificationService
        NotificationService.create_notification(
            recipient=user,
            title=f"Désinscription de {activity.title}",
            message=f"Vous vous êtes désinscrit de l'activité '{activity.title}'.",
            notification_type='activity_cancelled',
            content_object=activity
        )
        
        # Notifier le coach
        NotificationService.create_notification(
            recipient=activity.coach,
            title=f"Désinscription de {activity.title}",
            message=f"{user.get_full_name()} s'est désinscrit de votre activité '{activity.title}'.",
            notification_type='activity_cancelled',
            content_object=activity
        )
        
        return Response({
            'message': 'Désinscription réussie',
            'participants_count': activity.participants.count()
        })
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirmer une activité (admin uniquement)"""
        activity = self.get_object()
        
        # Vérifier les permissions - admin uniquement
        if request.user.role != 'admin':
            return Response(
                {'error': 'Permission refusée - Réservé aux administrateurs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que l'activité est en attente
        if activity.status != ActivityStatus.PENDING:
            return Response(
                {'error': 'Cette activité ne peut pas être confirmée'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier la disponibilité avant de confirmer (réservations et créneaux)
        from reservations.models import Reservation, ReservationStatus
        from timeslots.services import TimeSlotService as TSService

        terrain = activity.terrain
        start_time = activity.start_time
        end_time = activity.end_time

        reservation_conflict = Reservation.objects.filter(
            terrain=terrain,
            status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        activity_conflict = Activity.objects.filter(
            terrain=terrain,
            status=ActivityStatus.CONFIRMED,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(pk=activity.pk).exists()

        is_available_ts, ts_conflicts = TSService.check_availability(terrain, start_time, end_time)

        if reservation_conflict or activity_conflict or not is_available_ts:
            return Response({'error': 'Le terrain n\'est pas disponible pour cette période. Confirmation impossible.'}, status=status.HTTP_400_BAD_REQUEST)

        # Bloquer les créneaux et confirmer
        try:
            TSService.block_timeslots(terrain, start_time, end_time, reason=f"Activité: {activity.title}", created_by=request.user)
            activity.status = ActivityStatus.CONFIRMED
            activity.save()

            # Notification au coach
            from notifications.utils import NotificationService
            NotificationService.create_notification(
                recipient=activity.coach,
                title="Activité validée",
                message=f"Votre activité '{activity.title}' a été validée.",
                notification_type='activity_reminder',
                content_object=activity
            )

            return Response({
                'message': 'Activité confirmée avec succès',
                'status': activity.status
            })
        except Exception:
            return Response({'error': 'La confirmation a échoué lors du blocage des créneaux.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler une activité"""
        activity = self.get_object()
        
        # Vérifier les permissions
        user = request.user
        if user.role != 'admin' and activity.coach != user:
            return Response(
                {'error': 'Permission refusée'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        activity.status = ActivityStatus.CANCELLED
        activity.save()
        
        return Response({
            'message': 'Activité annulée avec succès',
            'status': activity.status
        })
    
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Réactiver une activité annulée (admin uniquement)"""
        activity = self.get_object()
        
        # Vérifier les permissions - admin uniquement
        if request.user.role != 'admin':
            return Response(
                {'error': 'Permission refusée - Réservé aux administrateurs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que l'activité est annulée
        if activity.status != ActivityStatus.CANCELLED:
            return Response(
                {'error': 'Cette activité ne peut pas être réactivée'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Réactiver l'activité (retour en attente)
        activity.status = ActivityStatus.PENDING
        activity.save()
        
        # Notification au coach
        from notifications.utils import NotificationService
        NotificationService.create_notification(
            recipient=activity.coach,
            title="Activité réactivée",
            message=f"Votre activité '{activity.title}' a été réactivée et est en attente de validation.",
            notification_type='activity_reminder',
            content_object=activity
        )
        
        # Notifier tous les admins de la réactivation
        User = get_user_model()
        admins = User.objects.filter(role='admin')
        
        for admin in admins:
            NotificationService.create_notification(
                recipient=admin,
                title="Activité réactivée",
                message=f"L'activité '{activity.title}' a été réactivée par {request.user.get_full_name()}.",
                notification_type='system_message',
                content_object=activity
            )
        
        return Response({
            'message': 'Activité réactivée avec succès',
            'status': activity.status
        })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_activities_view(request):
    """Récupérer les activités de l'utilisateur connecté"""
    user = request.user
    
    # Activités où l'utilisateur est coach
    coaching = Activity.objects.filter(coach=user)
    
    # Activités où l'utilisateur participe
    participating = Activity.objects.filter(participants=user)
    
    # Combiner et éviter les doublons
    activities = (coaching | participating).distinct().order_by('-start_time')
    
    serializer = ActivitySerializer(activities, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAdminOrCoach])
def all_activities_view(request):
    """Récupérer toutes les activités (admin et coach)"""
    activities = Activity.objects.all().order_by('-start_time')
    serializer = ActivitySerializer(activities, many=True)
    return Response(serializer.data)
