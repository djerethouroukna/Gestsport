from rest_framework import viewsets, status, permissions

from rest_framework.decorators import action, api_view, permission_classes

from rest_framework.response import Response

from django.contrib.auth import get_user_model

from django.db.models import Q

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.filters import SearchFilter, OrderingFilter

from django.utils import timezone

from decimal import Decimal



from users.api.permissions.user_permissions import (

    CanViewReservations, CanCreateReservation, CanValidateReservation, 

    IsOwnerOrAdmin, IsAdminOrCoach

)

from reservations.models import Reservation, ReservationStatus

from reservations.serializers import ReservationSerializer, ReservationCreateSerializer, ReservationListSerializer



User = get_user_model()



class ReservationViewSet(viewsets.ModelViewSet):

    """ViewSet pour la gestion des réservations"""

    serializer_class = ReservationSerializer

    permission_classes = [permissions.AllowAny]  # Temporairement pour les tests

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ['status', 'terrain', 'user']

    search_fields = ['terrain__name', 'user__first_name', 'user__last_name']

    ordering_fields = ['start_time', 'created_at']

    

    def get_queryset(self):

        """Filtrer les réservations selon le rôle de l'utilisateur"""

        user = self.request.user

        

        if user.role == 'admin':

            return Reservation.objects.all()

        elif user.role == 'coach':

            # Les coachs voient toutes les réservations

            return Reservation.objects.all()

        else:  # player

            # Les joueurs voient uniquement leurs réservations

            return Reservation.objects.filter(user=user)

    

    def get_permissions(self):

        """Permissions selon l'action"""

        if self.action == 'create':

            return [CanCreateReservation()]

        elif self.action == 'validate':

            return [CanValidateReservation()]

        elif self.action in ['update', 'partial_update', 'destroy']:

            return [IsOwnerOrAdmin()]

        else:  # list, retrieve

            return [CanViewReservations()]

    

    def perform_create(self, serializer):

        """Assigner l'utilisateur lors de la création"""

        reservation = serializer.save(user=self.request.user)

        

        # Notification automatique aux admins

        from notifications.utils import NotificationService

        from django.contrib.auth import get_user_model

        

        User = get_user_model()

        admins = User.objects.filter(role='admin')

        

        for admin in admins:

            NotificationService.create_notification(

                recipient=admin,

                title="Nouvelle réservation à valider",

                message=f"Nouvelle réservation du terrain {reservation.terrain.name} par {reservation.user.get_full_name()} pour le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')}.",

                notification_type='reservation_pending',

                content_object=reservation

            )

    

    @action(detail=True, methods=['post'])

    def validate(self, request, pk=None):

        """Valider une réservation (admin uniquement)"""

        reservation = self.get_object()

        reservation.status = ReservationStatus.CONFIRMED

        reservation.save()

        

        # Notification automatique au coach

        from notifications.utils import NotificationService

        NotificationService.create_notification(

            recipient=reservation.user,

            title="Réservation validée",

            message=f"Votre réservation du terrain {reservation.terrain.name} pour le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été validée.",

            notification_type='reservation_confirmed',

            content_object=reservation

        )

        

        return Response({

            'message': 'Réservation validée avec succès',

            'status': reservation.status,

            'notification_sent': True

        })

    

    @action(detail=True, methods=['post'])

    def reject(self, request, pk=None):

        """Rejeter une réservation (admin uniquement)"""

        reservation = self.get_object()

        reservation.status = ReservationStatus.REJECTED

        reservation.save()

        

        # Notification automatique au coach

        from notifications.utils import NotificationService

        NotificationService.create_notification(

            recipient=reservation.user,

            title="Réservation rejetée",

            message=f"Votre réservation du terrain {reservation.terrain.name} pour le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été rejetée.",

            notification_type='reservation_rejected',

            content_object=reservation

        )

        

        return Response({

            'message': 'Réservation rejetée',

            'status': reservation.status,

            'notification_sent': True

        })

    

    @action(detail=True, methods=['post'])

    def cancel(self, request, pk=None):

        """Annuler une réservation"""

        reservation = self.get_object()

        

        # Vérifier les permissions

        user = request.user

        if user.role != 'admin' and reservation.user != user:

            return Response(

                {'error': 'Permission refusée'}, 

                status=status.HTTP_403_FORBIDDEN

            )

        

        reservation.status = ReservationStatus.CANCELLED

        reservation.save()

        

        return Response({

            'message': 'Réservation annulée avec succès',

            'status': reservation.status

        })



@api_view(['GET'])

@permission_classes([CanViewReservations])

def my_reservations_view(request):

    """Récupérer les réservations de l'utilisateur connecté"""

    reservations = Reservation.objects.filter(user=request.user).order_by('-start_time')

    serializer = ReservationSerializer(reservations, many=True)

    return Response(serializer.data)



@api_view(['GET'])

@permission_classes([IsAdminOrCoach])

def all_reservations_view(request):

    """Récupérer toutes les réservations (admin et coach)"""

    reservations = Reservation.objects.all().order_by('-start_time')

    serializer = ReservationSerializer(reservations, many=True)

    return Response(serializer.data)

