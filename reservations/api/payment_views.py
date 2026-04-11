from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q

from reservations.models import Reservation, ReservationStatus
from notifications.utils import NotificationService
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def simulate_payment(request, reservation_id):
    """Simuler un paiement pour une réservation"""
    
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response(
            {'error': 'Réservation non trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier que l'utilisateur peut payer cette réservation
    user = request.user
    if user.role != 'admin' and reservation.user != user:
        return Response(
            {'error': 'Permission refusée'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Vérifier que la réservation est confirmée
    if reservation.status != ReservationStatus.CONFIRMED:
        return Response(
            {'error': 'Seules les réservations confirmées peuvent être payées'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Simuler le paiement
    payment_data = {
        'reservation_id': reservation.id,
        'amount': float(reservation.terrain.price_per_hour),
        'payment_method': request.data.get('payment_method', 'card'),
        'payment_date': timezone.now(),
        'status': 'completed',
        'transaction_id': f"SIM_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{reservation.id}"
    }
    
    # Notification à l'admin que le paiement a été effectué
    admins = User.objects.filter(role='admin')
    for admin in admins:
        NotificationService.create_notification(
            recipient=admin,
            title="Paiement effectué",
            message=f"Paiement de {payment_data['amount']} FCFA reçu pour la réservation du terrain {reservation.terrain.name} par {reservation.user.get_full_name()}.",
            notification_type='payment_completed',
            content_object=reservation
        )
    
    # Notification de confirmation au coach
    NotificationService.create_notification(
        recipient=reservation.user,
        title="Paiement confirmé",
        message=f"Votre paiement de {payment_data['amount']} FCFA pour la réservation du terrain {reservation.terrain.name} a été reçu avec succès.",
        notification_type='payment_confirmed',
        content_object=reservation
    )
    
    return Response({
        'message': 'Paiement simulé avec succès',
        'payment': payment_data,
        'reservation': {
            'id': reservation.id,
            'terrain': reservation.terrain.name,
            'date': reservation.start_time.strftime('%d/%m/%Y'),
            'time': reservation.start_time.strftime('%H:%M'),
            'status': reservation.status
        }
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_history(request):
    """Historique des paiements simulés pour un utilisateur"""
    
    user = request.user
    
    # Si admin, voir tous les paiements
    if user.role == 'admin':
        reservations = Reservation.objects.filter(
            status=ReservationStatus.CONFIRMED
        ).order_by('-start_time')
    else:
        # Sinon, voir seulement ses paiements
        reservations = Reservation.objects.filter(
            user=user,
            status=ReservationStatus.CONFIRMED
        ).order_by('-start_time')
    
    # Simuler l'historique des paiements
    payment_history = []
    for reservation in reservations:
        # Simuler que chaque réservation confirmée a été payée
        payment_history.append({
            'payment_id': f"SIM_{reservation.created_at.strftime('%Y%m%d_%H%M%S')}_{reservation.id}",
            'reservation_id': reservation.id,
            'terrain': reservation.terrain.name,
            'amount': float(reservation.terrain.price_per_hour),
            'payment_date': reservation.created_at + timezone.timedelta(minutes=30),  # Simulé 30min après réservation
            'status': 'completed',
            'payment_method': 'card',
            'user': reservation.user.get_full_name() if user.role == 'admin' else None
        })
    
    return Response({
        'payment_history': payment_history,
        'total_amount': sum(p['amount'] for p in payment_history),
        'total_payments': len(payment_history)
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def request_payment(request, reservation_id):
    """Demander un paiement pour une réservation (coach vers admin)"""
    
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response(
            {'error': 'Réservation non trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier que c'est le coach qui demande
    user = request.user
    if reservation.user != user:
        return Response(
            {'error': 'Seul le propriétaire peut demander le paiement'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Vérifier que la réservation est confirmée
    if reservation.status != ReservationStatus.CONFIRMED:
        return Response(
            {'error': 'La réservation doit être confirmée avant de demander le paiement'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Notifier les admins de la demande de paiement
    admins = User.objects.filter(role='admin')
    for admin in admins:
        NotificationService.create_notification(
            recipient=admin,
            title="Demande de paiement",
            message=f"{user.get_full_name()} demande à payer pour sa réservation du terrain {reservation.terrain.name} ({reservation.start_time.strftime('%d/%m/%Y à %H:%M')}).",
            notification_type='payment_requested',
            content_object=reservation
        )
    
    return Response({
        'message': 'Demande de paiement envoyée aux administrateurs',
        'reservation': {
            'id': reservation.id,
            'terrain': reservation.terrain.name,
            'amount': float(reservation.terrain.price_per_hour),
            'date': reservation.start_time.strftime('%d/%m/%Y'),
            'time': reservation.start_time.strftime('%H:%M')
        },
        'admins_notified': admins.count()
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_statistics(request):
    """Statistiques des paiements (admin uniquement)"""
    
    if request.user.role != 'admin':
        return Response(
            {'error': 'Accès refusé'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Statistiques basées sur les réservations confirmées
    confirmed_reservations = Reservation.objects.filter(
        status=ReservationStatus.CONFIRMED
    )
    
    total_revenue = 0
    payments_by_month = {}
    payments_by_terrain = {}
    payments_by_user = {}
    
    for reservation in confirmed_reservations:
        amount = float(reservation.terrain.price_per_hour)
        total_revenue += amount
        
        # Par mois
        month_key = reservation.start_time.strftime('%Y-%m')
        payments_by_month[month_key] = payments_by_month.get(month_key, 0) + amount
        
        # Par terrain
        terrain_name = reservation.terrain.name
        payments_by_terrain[terrain_name] = payments_by_terrain.get(terrain_name, 0) + amount
        
        # Par utilisateur
        user_name = reservation.user.get_full_name()
        payments_by_user[user_name] = payments_by_user.get(user_name, 0) + amount
    
    return Response({
        'total_revenue': total_revenue,
        'total_transactions': confirmed_reservations.count(),
        'average_amount': total_revenue / confirmed_reservations.count() if confirmed_reservations.exists() else 0,
        'payments_by_month': dict(sorted(payments_by_month.items())),
        'payments_by_terrain': dict(sorted(payments_by_terrain.items(), key=lambda x: x[1], reverse=True)),
        'top_payers': dict(sorted(payments_by_user.items(), key=lambda x: x[1], reverse=True)[:10])
    })
