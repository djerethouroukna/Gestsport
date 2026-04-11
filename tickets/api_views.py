# Vues API pour les scanners externes
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.db import transaction
import json
import logging

from .models import Ticket, Scan
from audit.models import AuditLog

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def scan_ticket_api(request):
    """API pour scanner un ticket"""
    try:
        # Récupérer les données du scan
        qr_data = request.data.get('qr_data', '')
        scanner_id = request.data.get('scanner_id', '')
        location = request.data.get('location', '')
        notes = request.data.get('notes', '')
        
        logger.info(f"Scan reçu - Scanner: {scanner_id}, QR: {qr_data[:50]}...")
        
        # Parser les données QR
        try:
            # Essayer de parser comme JSON
            ticket_data = json.loads(qr_data)
            ticket_number = ticket_data.get('ticket_number')
        except json.JSONDecodeError:
            # Si ce n'est pas du JSON, utiliser directement
            ticket_number = qr_data.strip()
        
        if not ticket_number:
            return Response({
                'success': False,
                'message': 'Numéro de ticket manquant',
                'error_code': 'MISSING_TICKET_NUMBER'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Trouver le ticket
        try:
            ticket = Ticket.objects.get(ticket_number=ticket_number)
        except Ticket.DoesNotExist:
            logger.warning(f"Ticket non trouvé: {ticket_number}")
            
            # Enregistrer dans l'audit log
            AuditLog.objects.create(
                user=request.user,
                action='SCAN',
                model_name='Ticket',
                object_id=None,
                object_repr=f'Ticket Invalide {ticket_number}',
                changes={
                    'scanner_id': scanner_id,
                    'location': location,
                    'ticket_number': ticket_number,
                    'error_code': 'INVALID_TICKET'
                },
                ip_address=request.META.get('REMOTE_ADDR', None),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={
                    'scan_type': 'INVALID',
                    'scanner_type': 'API'
                }
            )
            
            return Response({
                'success': False,
                'message': 'Ticket invalide',
                'error_code': 'INVALID_TICKET'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier la validité du ticket
        if ticket.is_used:
            logger.warning(f"Ticket déjà utilisé: {ticket_number}")
            return Response({
                'success': False,
                'message': 'Ticket déjà utilisé',
                'error_code': 'TICKET_ALREADY_USED',
                'used_at': ticket.used_at.isoformat() if ticket.used_at else None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier la réservation (autoriser jusqu'à 2 heures avant)
        reservation_start = ticket.reservation.start_time
        current_time = timezone.now()
        
        # Logs détaillés pour diagnostiquer les problèmes de temps
        logger.info(f"=== DIAGNOSTIC TEMPS POUR TICKET {ticket_number} ===")
        logger.info(f"Heure actuelle Django: {current_time}")
        logger.info(f"Heure réservation: {reservation_start}")
        logger.info(f"Timezone Django: {timezone.get_current_timezone()}")
        logger.info(f"Réservation > Actuel + 2h: {reservation_start > current_time + timezone.timedelta(hours=2)}")
        logger.info(f"Différence en heures: {(reservation_start - current_time).total_seconds() / 3600}")
        
        # Logique améliorée pour les réservations futures
        # Autoriser les réservations du jour même (même si dans quelques heures)
        # Rejeter uniquement les réservations des jours suivants
        current_date = current_time.date()
        reservation_date = reservation_start.date()
        
        # Si la réservation est pour un jour futur (pas aujourd'hui)
        if reservation_date > current_date:
            logger.warning(f"Réservation jour futur: {ticket_number} - Réservation: {reservation_date}, Aujourd'hui: {current_date}")
            return Response({
                'success': False,
                'message': 'Réservation pour un jour futur',
                'error_code': 'FUTURE_RESERVATION',
                'reservation_date': reservation_start.astimezone().strftime('%Y-%m-%d'),
                'reservation_time': reservation_start.astimezone().strftime('%H:%M'),
                'reservation_datetime': reservation_start.astimezone().strftime('%Y-%m-%d %H:%M:%S'),
                'reservation_timestamp': reservation_start.timestamp(),
                'reservation_iso': reservation_start.isoformat(),
                'start_time': reservation_start.astimezone().strftime('%H:%M:%S'),
                'end_time': ticket.reservation.end_time.astimezone().strftime('%H:%M:%S'),
                'start_datetime': reservation_start.astimezone().strftime('%Y-%m-%d %H:%M:%S'),
                'end_datetime': ticket.reservation.end_time.astimezone().strftime('%Y-%m-%d %H:%M:%S')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Si même jour mais plus de 4 heures dans le futur (pour éviter les erreurs)
        elif reservation_date == current_date and reservation_start > current_time + timezone.timedelta(hours=4):
            logger.warning(f"Réservation trop tard dans la journée: {ticket_number}")
            return Response({
                'success': False,
                'message': 'Réservation trop tardive (plus de 4h)',
                'error_code': 'FUTURE_RESERVATION',
                'reservation_date': reservation_start.astimezone().strftime('%Y-%m-%d'),
                'reservation_time': reservation_start.astimezone().strftime('%H:%M'),
                'reservation_datetime': reservation_start.astimezone().strftime('%Y-%m-%d %H:%M:%S'),
                'reservation_timestamp': reservation_start.timestamp(),
                'reservation_iso': reservation_start.isoformat(),
                'start_time': reservation_start.astimezone().strftime('%H:%M:%S'),
                'end_time': ticket.reservation.end_time.astimezone().strftime('%H:%M:%S'),
                'start_datetime': reservation_start.astimezone().strftime('%Y-%m-%d %H:%M:%S'),
                'end_datetime': ticket.reservation.end_time.astimezone().strftime('%Y-%m-%d %H:%M:%S')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier si la réservation est expirée
        if ticket.reservation.end_time < timezone.now():
            logger.warning(f"Réservation expirée: {ticket_number}")
            reservation_end = ticket.reservation.end_time
            return Response({
                'success': False,
                'message': 'Réservation expirée',
                'error_code': 'EXPIRED_RESERVATION',
                'reservation_date': reservation_end.astimezone().strftime('%Y-%m-%d'),
                'expiration_time': reservation_end.astimezone().strftime('%H:%M:%S'),
                'expiration_datetime': reservation_end.astimezone().strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': reservation_end.isoformat()
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer l'enregistrement de scan de manière atomique
        with transaction.atomic():
            # Créer l'enregistrement de scan
            scan = Scan.objects.create(
                scanner_id=scanner_id,
                ticket=ticket,
                location=location,
                is_valid=True,
                notes=notes
            )
            
            # Marquer le ticket comme utilisé
            ticket.is_used = True
            ticket.used_at = timezone.now()
            ticket.save()
            
            # Enregistrer dans l'audit log
            AuditLog.objects.create(
                user=request.user,
                action='SCAN',
                model_name='Ticket',
                object_id=ticket.id,
                object_repr=f'Ticket {ticket.ticket_number}',
                changes={
                    'scanner_id': scanner_id,
                    'location': location,
                    'scan_id': scan.id,
                    'scanned_at': scan.scanned_at.isoformat(),
                    'ticket_number': ticket.ticket_number,
                    'reservation_id': ticket.reservation.id,
                    'terrain': ticket.reservation.terrain.name,
                    'user': ticket.reservation.user.get_full_name() or ticket.reservation.user.username
                },
                ip_address=request.META.get('REMOTE_ADDR', None),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={
                    'scan_type': 'VALIDATION',
                    'scanner_type': 'API'
                }
            )
        
        logger.info(f"Ticket validé avec succès: {ticket_number}")
        
        # Retourner la réponse de succès
        return Response({
            'success': True,
            'message': 'Ticket validé avec succès',
            'ticket': {
                'ticket_number': ticket.ticket_number,
                'terrain_name': ticket.reservation.terrain.name,
                'date_formatted': ticket.reservation.start_time.strftime('%d/%m/%Y %H:%M'),
                'duration_minutes': str(ticket.reservation.duration_minutes),
                'user_name': ticket.reservation.user.get_full_name() or ticket.reservation.user.username,
                'activity': ticket.reservation.activity.title if ticket.reservation.activity else 'Réservation standard'
            },
            'validation': {
                'status': 'VALIDATED',
                'validated_at': scan.scanned_at.isoformat(),
                'scanner_id': scanner_id,
                'location': location,
                'scan_id': scan.id
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erreur lors du scan: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erreur serveur: {str(e)}',
            'error_code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def scanner_status(request):
    """API pour vérifier le statut du scanner"""
    scanner_id = request.GET.get('scanner_id', '')
    
    if not scanner_id:
        return Response({
            'success': False,
            'message': 'ID du scanner manquant',
            'error_code': 'MISSING_SCANNER_ID'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Vérifier les scans récents
        recent_scans = Scan.objects.filter(
            scanner_id=scanner_id,
            scanned_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()
        
        # Dernier scan
        last_scan = Scan.objects.filter(scanner_id=scanner_id).first()
        
        # Statistiques du scanner
        total_scans = Scan.objects.filter(scanner_id=scanner_id).count()
        
        return Response({
            'success': True,
            'scanner_id': scanner_id,
            'status': 'active',
            'scans_today': recent_scans,
            'total_scans': total_scans,
            'last_scan': {
                'scanned_at': last_scan.scanned_at.isoformat() if last_scan else None,
                'ticket_number': last_scan.ticket.ticket_number if last_scan else None,
                'location': last_scan.location if last_scan else None
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erreur statut scanner: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erreur serveur: {str(e)}',
            'error_code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def scan_history(request):
    """API pour voir l'historique des scans"""
    scanner_id = request.GET.get('scanner_id', '')
    limit = int(request.GET.get('limit', 50))
    
    try:
        scans = Scan.objects.filter(scanner_id=scanner_id).order_by('-scanned_at')[:limit]
        
        scan_data = []
        for scan in scans:
            scan_data.append({
                'scan_id': scan.id,
                'ticket_number': scan.ticket.ticket_number,
                'scanned_at': scan.scanned_at.isoformat(),
                'location': scan.location,
                'is_valid': scan.is_valid,
                'notes': scan.notes,
                'ticket_info': {
                    'terrain_name': scan.ticket.reservation.terrain.name,
                    'user_name': scan.ticket.reservation.user.get_full_name() or scan.ticket.reservation.user.username,
                    'duration_minutes': scan.ticket.reservation.duration_minutes
                }
            })
        
        return Response({
            'success': True,
            'scanner_id': scanner_id,
            'total_scans': len(scan_data),
            'scans': scan_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erreur historique scans: {str(e)}")
        return Response({
            'success': False,
            'message': f'Erreur serveur: {str(e)}',
            'error_code': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def verify_ticket_qr(request, ticket_number):
    """
    API pour vérifier un ticket via QR code
    Retourne les détails du ticket sans nécessiter d'authentification
    """
    try:
        print(f"=== VÉRIFICATION TICKET QR: {ticket_number} ===")
        
        # Rechercher le ticket par numéro
        ticket = get_object_or_404(Ticket, ticket_number=ticket_number)
        
        # Récupérer les détails de la réservation
        reservation = ticket.reservation
        
        # Construire la réponse
        ticket_data = {
            'success': True,
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'generated_at': ticket.generated_at.isoformat(),
                'is_used': ticket.is_used,
                'used_at': ticket.used_at.isoformat() if ticket.used_at else None,
                'is_valid': ticket.is_valid,
            },
            'reservation': {
                'id': reservation.id,
                'start_time': reservation.start_time.isoformat(),
                'end_time': reservation.end_time.isoformat(),
                'status': reservation.status,
                'total_amount': str(reservation.total_amount),
                'duration_minutes': reservation.duration_minutes,
            },
            'activity': {
                'id': reservation.activity.id,
                'title': reservation.activity.title,
                'type': reservation.activity.get_activity_type_display(),
                'coach': {
                    'name': reservation.activity.coach.get_full_name() or reservation.activity.coach.username,
                    'email': reservation.activity.coach.email,
                } if reservation.activity.coach else None,
            },
            'terrain': {
                'id': reservation.terrain.id,
                'name': reservation.terrain.name,
                'type': reservation.terrain.get_terrain_type_display(),
                'location': reservation.terrain.location,
            },
            'user': {
                'id': reservation.user.id,
                'name': reservation.user.get_full_name() or reservation.user.username,
                'email': reservation.user.email,
                'role': reservation.user.role,
            }
        }
        
        print(f"✅ Ticket {ticket_number} vérifié avec succès")
        return Response(ticket_data, status=status.HTTP_200_OK)
        
    except Ticket.DoesNotExist:
        print(f"❌ Ticket {ticket_number} non trouvé")
        return Response({
            'success': False,
            'error': 'Ticket non trouvé',
            'ticket_number': ticket_number
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        print(f"❌ Erreur vérification ticket: {e}")
        return Response({
            'success': False,
            'error': f'Erreur lors de la vérification: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def validate_ticket(request, ticket_number):
    """
    API pour valider l'utilisation d'un ticket
    Marque le ticket comme utilisé
    """
    try:
        print(f"=== VALIDATION TICKET: {ticket_number} ===")
        
        ticket = get_object_or_404(Ticket, ticket_number=ticket_number)
        
        # Vérifier si le ticket est déjà utilisé
        if ticket.is_used:
            return Response({
                'success': False,
                'error': 'Ticket déjà utilisé',
                'used_at': ticket.used_at.isoformat() if ticket.used_at else None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier si le ticket est valide
        if not ticket.is_valid:
            return Response({
                'success': False,
                'error': 'Ticket non valide (réservation non confirmée ou annulée)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Marquer le ticket comme utilisé
        ticket.is_used = True
        ticket.used_at = timezone.now()
        ticket.save(update_fields=['is_used', 'used_at'])
        
        print(f"✅ Ticket {ticket_number} validé à {ticket.used_at}")
        
        return Response({
            'success': True,
            'message': 'Ticket validé avec succès',
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'used_at': ticket.used_at.isoformat(),
            },
            'reservation': {
                'id': ticket.reservation.id,
                'user_name': ticket.reservation.user.get_full_name() or ticket.reservation.user.username,
                'activity_title': ticket.reservation.activity.title,
                'terrain_name': ticket.reservation.terrain.name,
            }
        }, status=status.HTTP_200_OK)
        
    except Ticket.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Ticket non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        print(f"❌ Erreur validation ticket: {e}")
        return Response({
            'success': False,
            'error': f'Erreur lors de la validation: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def ticket_info(request, ticket_number):
    """
    API publique pour obtenir les informations d'un ticket
    Accessible sans authentification pour les scanners
    """
    try:
        ticket = get_object_or_404(Ticket, ticket_number=ticket_number)
        reservation = ticket.reservation
        
        # Informations simplifiées pour le scanner
        simplified_data = {
            'ticket_number': ticket.ticket_number,
            'status': 'used' if ticket.is_used else 'valid' if ticket.is_valid else 'invalid',
            'activity': reservation.activity.title,
            'date': reservation.start_time.strftime('%d/%m/%Y'),
            'time': reservation.start_time.strftime('%H:%M'),
            'duration': f"{reservation.duration_minutes} minutes",
            'terrain': reservation.terrain.name,
            'participant': reservation.user.get_full_name() or reservation.user.username,
        }
        
        return Response(simplified_data, status=status.HTTP_200_OK)
        
    except Ticket.DoesNotExist:
        return Response({
            'error': 'Ticket non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)
