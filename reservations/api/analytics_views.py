# reservations/api/analytics_views.py - API pour les analytics unifiés
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

from reservations.analytics import ReservationAnalyticsService


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    """
    Tableau de bord principal avec statistiques unifiées
    """
    try:
        # Paramètres de période
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Vérification des permissions (admin voit tout, user voit ses stats)
        if request.user.role != 'admin':
            return Response({
                'error': 'Accès réservé aux administrateurs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        analytics_data = ReservationAnalyticsService.get_dashboard_summary(start_date, end_date)
        
        return Response({
            'success': True,
            'data': analytics_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def terrain_analytics(request, terrain_id):
    """
    Analytics détaillés pour un terrain spécifique
    """
    try:
        # Paramètres de période
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Vérification des permissions
        if request.user.role != 'admin':
            return Response({
                'error': 'Accès réservé aux administrateurs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        analytics_data = ReservationAnalyticsService.get_terrain_analytics(
            terrain_id, start_date, end_date
        )
        
        if 'error' in analytics_data:
            return Response({
                'success': False,
                'error': analytics_data['error']
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'data': analytics_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_analytics(request, user_id=None):
    """
    Analytics pour un utilisateur spécifique
    Si user_id n'est pas fourni, retourne les analytics de l'utilisateur connecté
    """
    try:
        # Déterminer l'utilisateur cible
        target_user_id = user_id if user_id else request.user.id
        
        # Vérification des permissions
        if request.user.role != 'admin' and target_user_id != request.user.id:
            return Response({
                'error': 'Accès refusé'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Paramètres de période
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        analytics_data = ReservationAnalyticsService.get_user_analytics(
            target_user_id, start_date, end_date
        )
        
        if 'error' in analytics_data:
            return Response({
                'success': False,
                'error': analytics_data['error']
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'data': analytics_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def revenue_analytics(request):
    """
    Analytics détaillés des revenus
    """
    try:
        # Vérification des permissions
        if request.user.role != 'admin':
            return Response({
                'error': 'Accès réservé aux administrateurs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Paramètres de période
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        analytics_data = ReservationAnalyticsService.get_revenue_analytics(start_date, end_date)
        
        return Response({
            'success': True,
            'data': analytics_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def occupancy_analytics(request):
    """
    Analytics des taux d'occupation
    """
    try:
        # Vérification des permissions
        if request.user.role != 'admin':
            return Response({
                'error': 'Accès réservé aux administrateurs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Paramètres de période
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        analytics_data = ReservationAnalyticsService.get_occupancy_analytics(start_date, end_date)
        
        return Response({
            'success': True,
            'data': analytics_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def quick_stats(request):
    """
    Statistiques rapides pour le tableau de bord
    """
    try:
        # Période par défaut : aujourd'hui
        today = timezone.now().date()
        start_of_day = timezone.make_aware(
            datetime.combine(today, datetime.min.time())
        )
        end_of_day = timezone.make_aware(
            datetime.combine(today, datetime.max.time())
        )
        
        # Stats du jour
        from reservations.models import Reservation, ReservationStatus
        from payments.models import Payment, PaymentStatus
        
        today_stats = Reservation.objects.filter(
            created_at__range=[start_of_day, end_of_day]
        ).aggregate(
            total_reservations=Count('id'),
            pending_reservations=Count('id', filter=Q(status=ReservationStatus.PENDING)),
            confirmed_reservations=Count('id', filter=Q(status=ReservationStatus.CONFIRMED)),
            completed_reservations=Count('id', filter=Q(status=ReservationStatus.COMPLETED))
        )
        
        # Revenus du jour
        today_revenue = Payment.objects.filter(
            created_at__range=[start_of_day, end_of_day],
            status=PaymentStatus.COMPLETED
        ).aggregate(
            total_revenue=Sum('amount'),
            transaction_count=Count('id')
        )
        
        # Stats de la semaine
        week_ago = timezone.now() - timedelta(days=7)
        week_stats = Reservation.objects.filter(
            created_at__range=[week_ago, timezone.now()]
        ).aggregate(
            total_reservations=Count('id'),
            completed_reservations=Count('id', filter=Q(status=ReservationStatus.COMPLETED))
        )
        
        # Revenus de la semaine
        week_revenue = Payment.objects.filter(
            created_at__range=[week_ago, timezone.now()],
            status=PaymentStatus.COMPLETED
        ).aggregate(
            total_revenue=Sum('amount')
        )
        
        # Réservations en attente
        pending_reservations = Reservation.objects.filter(
            status=ReservationStatus.PENDING
        ).count()
        
        # Terrains les plus populaires aujourd'hui
        popular_terrains = Reservation.objects.filter(
            created_at__range=[start_of_day, end_of_day]
        ).values('terrain__name').annotate(
            reservation_count=Count('id')
        ).order_by('-reservation_count')[:5]
        
        response_data = {
            "today": {
                "reservations": today_stats,
                "revenue": today_revenue,
                "popular_terrains": list(popular_terrains)
            },
            "week": {
                "reservations": week_stats,
                "revenue": week_revenue
            },
            "pending": {
                "count": pending_reservations
            }
        }
        
        return Response({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
