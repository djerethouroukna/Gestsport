# tickets/api_external.py
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
import json
import logging

from .models import Ticket
from reservations.models import Reservation
from .permissions import log_external_request, rate_limiter

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def external_ticket_validation(request):
    """
    API externe pour validation de tickets par système de scan externe
    Endpoint: /api/external/ticket/validate/
    
    Méthodes supportées:
    - GET: Validation par QR code (paramètre qr_data)
    - POST: Validation par JSON body
    """
    
    # Logger la requête
    log_external_request(request, 'external_ticket_validation')
    
    # Rate limiting
    client_ip = get_client_ip(request)
    if not rate_limiter.is_allowed(client_ip):
        return JsonResponse({
            'error': 'Rate limit exceeded',
            'code': 'RATE_LIMIT_EXCEEDED'
        }, status=429)
    
    try:
        # Récupérer les données du QR code
        qr_data = None
        
        if request.method == 'GET':
            qr_data = request.GET.get('qr_data')
            ticket_number = request.GET.get('ticket_number')
        else:  # POST
            try:
                body_data = json.loads(request.body)
                qr_data = body_data.get('qr_data')
                ticket_number = body_data.get('ticket_number')
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'Invalid JSON format',
                    'code': 'INVALID_JSON'
                }, status=400)
        
        # Validation des entrées
        if not qr_data and not ticket_number:
            return JsonResponse({
                'error': 'QR data or ticket number is required',
                'code': 'MISSING_DATA'
            }, status=400)
        
        # Extraire le numéro de ticket des données QR
        if qr_data:
            try:
                qr_info = json.loads(qr_data)
                ticket_number = qr_info.get('ticket_number')
            except (json.JSONDecodeError, TypeError):
                return JsonResponse({
                    'error': 'Invalid QR data format',
                    'code': 'INVALID_QR_FORMAT'
                }, status=400)
        
        if not ticket_number:
            return JsonResponse({
                'error': 'Ticket number not found in QR data',
                'code': 'TICKET_NUMBER_MISSING'
            }, status=400)
        
        print(f"Numéro de ticket à valider: {ticket_number}")
        
        # Récupérer le ticket avec toutes les relations
        try:
            ticket = Ticket.objects.select_related(
                'reservation',
                'reservation__user',
                'reservation__terrain',
                'reservation__activity',
                'used_by'
            ).get(ticket_number=ticket_number)
            
            print(f"Ticket trouvé: {ticket}")
            
        except Ticket.DoesNotExist:
            print(f"❌ Ticket {ticket_number} non trouvé")
            return JsonResponse({
                'error': 'Ticket not found',
                'code': 'TICKET_NOT_FOUND',
                'ticket_number': ticket_number
            }, status=404)
        
        # Validation du ticket
        validation_result = validate_ticket_external(ticket, request)
        
        print(f"Résultat validation: {validation_result}")
        
        return JsonResponse(validation_result)
        
    except Exception as e:
        logger.error(f"Erreur API externe: {str(e)}")
        print(f"❌ Erreur API: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'message': str(e)
        }, status=500)


def validate_ticket_external(ticket, request):
    """
    Logique de validation pour système externe
    """
    reservation = ticket.reservation
    
    # Vérifier si le ticket est déjà utilisé
    if ticket.is_used:
        return {
            'success': False,
            'error': 'Ticket already used',
            'code': 'TICKET_ALREADY_USED',
            'ticket': {
                'ticket_number': ticket.ticket_number,
                'status': 'USED',
                'used_at': ticket.used_at.isoformat() if ticket.used_at else None,
                'used_by': ticket.used_by.get_full_name() if ticket.used_by else None,
                'reservation_id': reservation.id,
                'terrain': reservation.terrain.name,
                'date': reservation.start_time.isoformat(),
                'activity': reservation.activity.title if reservation.activity else None
            }
        }
    
    # Vérifier si la réservation est confirmée
    if reservation.status != 'confirmed':
        return {
            'success': False,
            'error': 'Reservation not confirmed',
            'code': 'RESERVATION_NOT_CONFIRMED',
            'ticket': {
                'ticket_number': ticket.ticket_number,
                'status': 'RESERVATION_PENDING',
                'reservation_status': reservation.status,
                'reservation_id': reservation.id
            }
        }
    
    # Vérifier si la date est valide (pas dans le passé)
    if reservation.start_time < timezone.now():
        return {
            'success': False,
            'error': 'Reservation date expired',
            'code': 'RESERVATION_EXPIRED',
            'ticket': {
                'ticket_number': ticket.ticket_number,
                'status': 'EXPIRED',
                'reservation_date': reservation.start_time.isoformat(),
                'current_date': timezone.now().isoformat()
            }
        }
    
    # Validation réussie - Marquer le ticket comme utilisé
    with transaction.atomic():
        ticket.is_used = True
        ticket.used_at = timezone.now()
        ticket.used_by = None  # Système externe, pas d'utilisateur Django
        ticket.save()
        
        print(f"✅ Ticket {ticket.ticket_number} validé avec succès")
    
    return {
        'success': True,
        'message': 'Ticket validated successfully',
        'code': 'TICKET_VALIDATED',
        'ticket': {
            'ticket_number': ticket.ticket_number,
            'status': 'VALIDATED',
            'validated_at': ticket.used_at.isoformat(),
            'reservation_id': reservation.id,
            'terrain': reservation.terrain.name,
            'terrain_type': reservation.terrain.get_terrain_type_display(),
            'date': reservation.start_time.isoformat(),
            'end_time': reservation.end_time.isoformat(),
            'duration_minutes': reservation.duration_minutes,
            'activity': reservation.activity.title if reservation.activity else None,
            'activity_type': reservation.activity.get_activity_type_display() if reservation.activity else None,
            'coach': reservation.user.get_full_name() or reservation.user.username,
            'participant_count': reservation.activity.max_participants if reservation.activity else None
        }
    }


@csrf_exempt
@require_http_methods(["GET"])
def external_ticket_info(request):
    """
    API externe pour obtenir les informations d'un ticket sans validation
    Endpoint: /api/external/ticket/info/
    
    Paramètres:
    - ticket_number: Numéro du ticket
    - qr_data: Données QR code (optionnel)
    """
    
    try:
        ticket_number = request.GET.get('ticket_number')
        qr_data = request.GET.get('qr_data')
        
        # Extraire le numéro des données QR si fourni
        if qr_data and not ticket_number:
            try:
                qr_info = json.loads(qr_data)
                ticket_number = qr_info.get('ticket_number')
            except (json.JSONDecodeError, TypeError):
                return JsonResponse({
                    'error': 'Invalid QR data format',
                    'code': 'INVALID_QR_FORMAT'
                }, status=400)
        
        if not ticket_number:
            return JsonResponse({
                'error': 'Ticket number is required',
                'code': 'TICKET_NUMBER_REQUIRED'
            }, status=400)
        
        # Récupérer le ticket
        try:
            ticket = Ticket.objects.select_related(
                'reservation',
                'reservation__user',
                'reservation__terrain',
                'reservation__activity'
            ).get(ticket_number=ticket_number)
            
        except Ticket.DoesNotExist:
            return JsonResponse({
                'error': 'Ticket not found',
                'code': 'TICKET_NOT_FOUND'
            }, status=404)
        
        # Retourner les informations sans validation
        reservation = ticket.reservation
        
        return JsonResponse({
            'success': True,
            'ticket': {
                'ticket_number': ticket.ticket_number,
                'status': 'USED' if ticket.is_used else 'VALID',
                'generated_at': ticket.generated_at.isoformat(),
                'used_at': ticket.used_at.isoformat() if ticket.used_at else None,
                'reservation': {
                    'id': reservation.id,
                    'status': reservation.status,
                    'terrain': reservation.terrain.name,
                    'terrain_type': reservation.terrain.get_terrain_type_display(),
                    'start_time': reservation.start_time.isoformat(),
                    'end_time': reservation.end_time.isoformat(),
                    'duration_minutes': reservation.duration_minutes,
                    'activity': reservation.activity.title if reservation.activity else None,
                    'activity_type': reservation.activity.get_activity_type_display() if reservation.activity else None,
                    'coach': reservation.user.get_full_name() or reservation.user.username,
                    'participant_count': reservation.activity.max_participants if reservation.activity else None
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur API info: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def external_system_status(request):
    """
    API externe pour vérifier le statut du système
    Endpoint: /api/external/status/
    """
    
    try:
        # Statistiques du système
        total_tickets = Ticket.objects.count()
        used_tickets = Ticket.objects.filter(is_used=True).count()
        valid_tickets = total_tickets - used_tickets
        
        # Réservations du jour
        today = timezone.now().date()
        today_reservations = Reservation.objects.filter(
            start_time__date=today,
            status='confirmed'
        ).count()
        
        return JsonResponse({
            'success': True,
            'system': {
                'status': 'online',
                'version': '1.0.0',
                'timestamp': timezone.now().isoformat()
            },
            'statistics': {
                'tickets': {
                    'total': total_tickets,
                    'used': used_tickets,
                    'valid': valid_tickets
                },
                'reservations': {
                    'today': today_reservations,
                    'confirmed': Reservation.objects.filter(status='confirmed').count(),
                    'pending': Reservation.objects.filter(status='pending').count()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur API status: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=500)


def get_client_ip(request):
    """
    Extraire l'IP réelle du client
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Documentation API externe
EXTERNAL_API_DOCS = {
    'title': 'GestSport External Scanner API',
    'version': '1.0.0',
    'endpoints': {
        'validate': {
            'url': '/api/external/ticket/validate/',
            'method': 'GET/POST',
            'description': 'Valider un ticket avec QR code',
            'parameters': {
                'qr_data': 'Données QR code (JSON string)',
                'ticket_number': 'Numéro de ticket (optionnel si qr_data fourni)'
            },
            'responses': {
                '200': 'Validation réussie',
                '400': 'Erreur de requête',
                '404': 'Ticket non trouvé',
                '500': 'Erreur serveur'
            }
        },
        'info': {
            'url': '/api/external/ticket/info/',
            'method': 'GET',
            'description': 'Obtenir les informations d\'un ticket',
            'parameters': {
                'ticket_number': 'Numéro du ticket',
                'qr_data': 'Données QR code (optionnel)'
            }
        },
        'status': {
            'url': '/api/external/status/',
            'method': 'GET',
            'description': 'Statut du système et statistiques'
        }
    }
}
