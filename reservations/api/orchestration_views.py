# reservations/api/orchestration_views.py - API unifiée pour réservation complète
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime
from decimal import Decimal

from reservations.services import ReservationOrchestrationService
from reservations.models import Reservation
from terrains.models import Terrain
from notifications.utils import NotificationService

User = get_user_model()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_complete_reservation(request):
    """
    Endpoint unifié pour créer une réservation complète
    Gère tout le workflow: vérification → tarification → création → paiement → confirmation
    """
    try:
        data = JSONParser().parse(request)
        
        # Validation des données requises
        required_fields = ['terrain_id', 'start_datetime', 'end_datetime']
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f'Le champ {field} est requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Récupération des objets
        try:
            terrain = Terrain.objects.get(id=data['terrain_id'])
        except Terrain.DoesNotExist:
            return Response(
                {'error': 'Terrain non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Conversion des dates
        start_datetime = datetime.fromisoformat(data['start_datetime'].replace('Z', '+00:00'))
        end_datetime = datetime.fromisoformat(data['end_datetime'].replace('Z', '+00:00'))
        
        # Options supplémentaires
        notes = data.get('notes', '')
        payment_method_id = data.get('payment_method_id')
        use_subscription = data.get('use_subscription', False)
        use_credits = data.get('use_credits', False)
        
        # Création de la réservation via le service d'orchestration
        result = ReservationOrchestrationService.create_complete_reservation(
            user=request.user,
            terrain=terrain,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            notes=notes,
            payment_method_id=payment_method_id,
            use_subscription=use_subscription,
            use_credits=use_credits
        )
        
        if result['success']:
            # Sérialisation des données pour la réponse
            reservation_data = {
                'id': result['reservation'].id,
                'user': {
                    'id': result['reservation'].user.id,
                    'name': result['reservation'].user.get_full_name(),
                    'email': result['reservation'].user.email
                },
                'terrain': {
                    'id': result['reservation'].terrain.id,
                    'name': result['reservation'].terrain.name,
                    'type': result['reservation'].terrain.terrain_type
                },
                'start_time': result['reservation'].start_time.isoformat(),
                'end_time': result['reservation'].end_time.isoformat(),
                'status': result['reservation'].status,
                'notes': result['reservation'].notes,
                'created_at': result['reservation'].created_at.isoformat(),
                'pricing': result['pricing'],
                'payment': {
                    'id': result['payment'].id,
                    'amount': float(result['payment'].amount),
                    'status': result['payment'].status,
                    'is_simulated': result['payment'].is_simulated
                } if result['payment'] else None,
                'subscription': {
                    'id': result['subscription'].id,
                    'name': result['subscription'].membership.name,
                    'discount': float(result['subscription'].membership.discount_percentage)
                } if result['subscription'] else None,
                'credits_used': float(result['credits_used']) if result['credits_used'] else 0
            }
            
            return Response({
                'success': True,
                'message': 'Réservation créée avec succès',
                'reservation': reservation_data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': result['error'],
                'conflicts': result.get('conflicts', []),
                'waiting_list': result.get('waiting_list')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_reservation(request, reservation_id):
    """
    Endpoint pour annuler une réservation
    Gère le remboursement et la libération des ressources
    """
    try:
        try:
            reservation = Reservation.objects.get(id=reservation_id)
        except Reservation.DoesNotExist:
            return Response(
                {'error': 'Réservation non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Vérification des permissions
        if (request.user.role != 'admin' and 
            reservation.user != request.user):
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', '')
        
        # Annulation via le service d'orchestration
        result = ReservationOrchestrationService.cancel_reservation(
            reservation=reservation,
            cancelled_by=request.user,
            reason=reason
        )
        
        if result['success']:
            return Response({
                'success': True,
                'message': 'Réservation annulée avec succès',
                'refund_amount': float(result['refund_amount']),
                'waiting_list_notified': result['waiting_list_notified']
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_reservation_details(request, reservation_id):
    """
    Endpoint pour récupérer tous les détails d'une réservation
    Inclut les informations de tous les modules connectés
    """
    try:
        result = ReservationOrchestrationService.get_reservation_details(reservation_id)
        
        if result['success']:
            details = result['details']
            
            # Sérialisation des données
            reservation_data = {
                'reservation': {
                    'id': details['reservation'].id,
                    'user': {
                        'id': details['reservation'].user.id,
                        'name': details['reservation'].user.get_full_name(),
                        'email': details['reservation'].user.email,
                        'role': details['reservation'].user.role
                    },
                    'terrain': {
                        'id': details['reservation'].terrain.id,
                        'name': details['reservation'].terrain.name,
                        'type': details['reservation'].terrain.terrain_type,
                        'capacity': details['reservation'].terrain.capacity,
                        'price_per_hour': float(details['reservation'].terrain.price_per_hour)
                    },
                    'start_time': details['reservation'].start_time.isoformat(),
                    'end_time': details['reservation'].end_time.isoformat(),
                    'status': details['reservation'].status,
                    'notes': details['reservation'].notes,
                    'created_at': details['reservation'].created_at.isoformat(),
                    'updated_at': details['reservation'].updated_at.isoformat()
                },
                'timeslot': {
                    'id': details['timeslot'].id,
                    'date': details['timeslot'].date.isoformat(),
                    'start_time': details['timeslot'].start_time.isoformat(),
                    'end_time': details['timeslot'].end_time.isoformat(),
                    'status': details['timeslot'].status,
                    'duration_minutes': details['timeslot'].duration_minutes
                } if details['timeslot'] else None,
                'payment': {
                    'id': details['payment'].id,
                    'amount': float(details['payment'].amount),
                    'status': details['payment'].status,
                    'is_simulated': details['payment'].is_simulated,
                    'paid_at': details['payment'].paid_at.isoformat() if details['payment'].paid_at else None
                } if details['payment'] else None,
                'price_history': {
                    'base_price': float(details['price_history'].base_price),
                    'final_price': float(details['price_history'].final_price),
                    'total_discount': float(details['price_history'].total_discount),
                    'discount_percentage': float(details['price_history'].discount_percentage),
                    'applied_rules': details['price_history'].applied_rules
                } if details['price_history'] else None,
                'subscription': {
                    'id': details['subscription'].id,
                    'name': details['subscription'].membership.name,
                    'status': details['subscription'].status,
                    'end_date': details['subscription'].end_date.isoformat(),
                    'reservations_used_this_month': details['subscription'].reservations_used_this_month,
                    'hours_used_this_month': details['subscription'].hours_used_this_month
                } if details['subscription'] else None,
                'user_credits': [
                    {
                        'id': credit.id,
                        'amount': float(credit.amount),
                        'credit_type': credit.credit_type,
                        'expires_at': credit.expires_at.isoformat() if credit.expires_at else None,
                        'is_available': credit.is_available
                    }
                    for credit in details['user_credits']
                ],
                'waiting_list_entry': {
                    'id': details['waiting_list_entry'].id,
                    'priority': details['waiting_list_entry'].priority,
                    'status': details['waiting_list_entry'].status,
                    'days_in_waiting': details['waiting_list_entry'].days_in_waiting
                } if details['waiting_list_entry'] else None
            }
            
            return Response({
                'success': True,
                'details': reservation_data
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_availability_and_pricing(request):
    """
    Endpoint pour vérifier la disponibilité et calculer le prix
    Utile pour le frontend avant de créer une réservation
    """
    try:
        data = JSONParser().parse(request)
        
        # Validation des données requises
        required_fields = ['terrain_id', 'start_datetime', 'end_datetime']
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f'Le champ {field} est requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Récupération des objets
        try:
            terrain = Terrain.objects.get(id=data['terrain_id'])
        except Terrain.DoesNotExist:
            return Response(
                {'error': 'Terrain non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Conversion des dates
        start_datetime = datetime.fromisoformat(data['start_datetime'].replace('Z', '+00:00'))
        end_datetime = datetime.fromisoformat(data['end_datetime'].replace('Z', '+00:00'))
        
        # Vérification de disponibilité
        from reservations.services import TimeSlotService
        is_available, conflicts = TimeSlotService.check_availability(
            terrain, start_datetime, end_datetime
        )
        
        # Calcul du prix
        from pricing.services import DynamicPricingService
        pricing_result = DynamicPricingService.calculate_price(
            terrain=terrain,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            user=request.user
        )
        
        # Vérification des abonnements/crédits
        from reservations.services import SubscriptionService, CreditService
        
        subscription_result = SubscriptionService.get_best_subscription(request.user, terrain)
        credit_result = CreditService.use_available_credits(request.user, pricing_result['final_price'])
        
        response_data = {
            'success': True,
            'available': is_available,
            'conflicts': [
                {
                    'terrain': conflict.terrain.name,
                    'date': conflict.date.isoformat(),
                    'start_time': conflict.start_time.isoformat(),
                    'end_time': conflict.end_time.isoformat()
                }
                for conflict in conflicts
            ] if conflicts else [],
            'pricing': {
                'base_price': float(pricing_result['base_price']),
                'final_price': float(pricing_result['final_price']),
                'total_discount': float(pricing_result['total_discount']),
                'discount_percentage': float(pricing_result['discount_percentage']),
                'applied_rules': pricing_result['applied_rules']
            },
            'subscription': {
                'available': subscription_result['success'],
                'discount': float(subscription_result['discount']) if subscription_result['success'] else 0,
                'name': subscription_result['subscription'].membership.name if subscription_result['success'] else None
            },
            'credits': {
                'available': credit_result['success'],
                'total_available': float(credit_result['available']) if not credit_result['success'] else sum(credit['amount'] for credit in credit_result['used_credits']),
                'can_cover': credit_result['success']
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user_reservations_summary(request):
    """
    Endpoint pour obtenir un résumé des réservations de l'utilisateur
    Inclut les statistiques et informations importantes
    """
    try:
        user = request.user
        
        # Réservations actives
        active_reservations = Reservation.objects.filter(
            user=user,
            status__in=['pending', 'confirmed']
        ).order_by('start_time')
        
        # Réservations passées
        past_reservations = Reservation.objects.filter(
            user=user,
            status__in=['completed', 'cancelled']
        ).order_by('-start_time')[:10]
        
        # Statistiques
        total_reservations = Reservation.objects.filter(user=user).count()
        total_amount_paid = sum(
            payment.amount for payment in 
            Payment.objects.filter(reservation__user=user, status='completed')
        )
        
        # Abonnement actif
        from reservations.services import SubscriptionService
        active_subscription = None
        subscriptions = Subscription.objects.filter(
            user=user,
            status='active',
            end_date__gt=timezone.now()
        ).select_related('membership').first()
        
        if subscriptions:
            active_subscription = {
                'id': subscriptions.id,
                'name': subscriptions.membership.name,
                'end_date': subscriptions.end_date.isoformat(),
                'reservations_used': subscriptions.reservations_used_this_month,
                'max_reservations': subscriptions.membership.max_reservations_per_month,
                'hours_used': subscriptions.hours_used_this_month,
                'max_hours': subscriptions.membership.included_hours_per_month
            }
        
        # Crédits disponibles
        from reservations.services import CreditService
        user_credits = UserCredit.objects.filter(
            user=user,
            is_active=True,
            amount__gt=0
        ).order_by('expires_at')
        
        total_credits = sum(credit.amount for credit in user_credits)
        
        response_data = {
            'success': True,
            'summary': {
                'total_reservations': total_reservations,
                'active_reservations': active_reservations.count(),
                'total_amount_paid': float(total_amount_paid),
                'active_subscription': active_subscription,
                'total_credits': float(total_credits),
                'credits_breakdown': [
                    {
                        'id': credit.id,
                        'amount': float(credit.amount),
                        'credit_type': credit.credit_type,
                        'expires_at': credit.expires_at.isoformat() if credit.expires_at else None
                    }
                    for credit in user_credits
                ]
            },
            'active_reservations': [
                {
                    'id': res.id,
                    'terrain': res.terrain.name,
                    'start_time': res.start_time.isoformat(),
                    'end_time': res.end_time.isoformat(),
                    'status': res.status,
                    'amount': float(res.total_amount)
                }
                for res in active_reservations
            ],
            'recent_reservations': [
                {
                    'id': res.id,
                    'terrain': res.terrain.name,
                    'start_time': res.start_time.isoformat(),
                    'end_time': res.end_time.isoformat(),
                    'status': res.status,
                    'amount': float(res.total_amount)
                }
                for res in past_reservations
            ]
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Erreur technique: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
