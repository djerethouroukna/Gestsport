# tickets/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
from io import BytesIO

from reservations.models import Reservation
from .models import Ticket
from .services import TicketService


@login_required
def generate_ticket(request, reservation_id):
    """Génère un ticket pour réservation confirmée"""
    print(f"=== GÉNÉRATION TICKET POUR RÉSERVATION {reservation_id} ===")
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    print(f"Réservation: {reservation}")
    print(f"User: {request.user}")
    print(f"Status: {reservation.status}")
    
    # Vérifications
    if reservation.user != request.user and request.user.role != 'admin':
        print("[ERREUR] Permission refusée")
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    if reservation.status != 'confirmed':
        print("[ERREUR] Réservation non confirmée")
        return JsonResponse({'error': 'Réservation non confirmée'}, status=400)
    
    # Si le ticket existe déjà, le télécharger directement
    if hasattr(reservation, 'ticket') and reservation.ticket:
        print(f"[OK] Ticket déjà existant: {reservation.ticket.ticket_number}")
        ticket = reservation.ticket
        
        # Générer le PDF
        pdf_buffer = TicketService.generate_ticket_pdf(ticket)
        print("[OK] PDF généré pour ticket existant")
        
        # Retourner le PDF
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'
        print("[OK] PDF envoyé pour ticket existant")
        
        return response
    
    try:
        # Créer le ticket avec gestion des erreurs
        with transaction.atomic():
            # Vérifier d'abord si un ticket existe
            existing_ticket = Ticket.objects.filter(reservation=reservation).first()
            if existing_ticket:
                print(f"[ERREUR] Ticket existe déjà: {existing_ticket.ticket_number}")
                return JsonResponse({'error': 'Ticket déjà généré pour cette réservation', 'ticket_number': existing_ticket.ticket_number}, status=400)
            
            ticket = Ticket.objects.create(reservation=reservation)
            print(f"[OK] Ticket créé: {ticket.ticket_number}")
            
            # Générer le PDF
            pdf_buffer = TicketService.generate_ticket_pdf(ticket)
            print("[OK] PDF généré")
            
            # Retourner le PDF
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'
            print("[OK] PDF envoyé")
            
            return response
            
    except Exception as e:
        print(f"[ERREUR] Erreur génération ticket: {e}")
        # Gérer spécifiquement les erreurs de clé dupliquée
        if "duplicate key" in str(e).lower() or "tickets_ticket_pkey" in str(e):
            return JsonResponse({'error': 'Un ticket existe déjà pour cette réservation'}, status=409)
        else:
            return JsonResponse({'error': f'Erreur: {str(e)}'}, status=500)


@login_required
def download_ticket(request, reservation_id):
    """Télécharge un ticket existant"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifications
    if reservation.user != request.user and request.user.role != 'admin':
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    # Vérifier si un ticket existe pour cette réservation
    try:
        ticket = reservation.ticket
    except:
        return JsonResponse({'error': 'Ticket non trouvé'}, status=404)
    
    # Générer le PDF
    pdf_buffer = TicketService.generate_ticket_pdf(ticket)
    
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'
    return response


@login_required
def scan_ticket_view(request):
    """Interface de scan des tickets"""
    return render(request, 'tickets/scan_ticket.html')


@csrf_exempt
@require_POST
def scan_ticket_api(request):
    """API pour scanner et valider un ticket"""
    print(f"=== SCAN TICKET API ===")
    print(f"User: {request.user}")
    
    try:
        data = json.loads(request.body)
        qr_data = data.get('qr_data')
        
        if not qr_data:
            return JsonResponse({'error': 'Données QR manquantes'}, status=400)
        
        # Parser les données QR
        ticket_info = json.loads(qr_data)
        ticket_number = ticket_info.get('ticket_number')
        
        print(f"Ticket number: {ticket_number}")
        
        # Récupérer le ticket
        ticket = Ticket.objects.select_related('reservation', 'reservation__user', 'reservation__terrain').get(
            ticket_number=ticket_number
        )
        
        print(f"Ticket trouvé: {ticket}")
        
        # Vérifications
        if ticket.is_used:
            print("❌ Ticket déjà utilisé")
            return JsonResponse({
                'error': 'Ticket déjà utilisé',
                'used_at': ticket.used_at,
                'used_by': ticket.used_by.get_full_name() if ticket.used_by else None
            }, status=400)
        
        # Vérifier si l'utilisateur est autorisé à scanner
        user = request.user
        reservation = ticket.reservation
        
        # L'entraîneur ne peut scanner que ses propres réservations
        if user.role == 'coach' and reservation.user != user:
            print("❌ Coach non autorisé")
            return JsonResponse({'error': 'Non autorisé à scanner ce ticket'}, status=403)
        
        # Admin peut scanner tous les tickets
        if user.role not in ['admin', 'coach']:
            print("❌ Rôle non autorisé")
            return JsonResponse({'error': 'Non autorisé'}, status=403)
        
        # Valider le ticket
        with transaction.atomic():
            ticket.is_used = True
            ticket.used_at = timezone.now()
            ticket.used_by = user
            ticket.save()
            
            print(f"✅ Ticket validé par {user}")
        
        return JsonResponse({
            'success': True,
            'message': 'Ticket validé avec succès',
            'ticket': {
                'number': ticket.ticket_number,
                'activity': reservation.activity.title if reservation.activity else 'Réservation standard',
                'terrain': reservation.terrain.name,
                'date': reservation.start_time.isoformat(),
                'coach': reservation.user.get_full_name(),
                'validated_at': ticket.used_at.isoformat(),
                'validated_by': user.get_full_name()
            }
        })
        
    except Ticket.DoesNotExist:
        print("❌ Ticket introuvable")
        return JsonResponse({'error': 'Ticket invalide'}, status=404)
    except Exception as e:
        print(f"❌ Erreur scan: {e}")
        return JsonResponse({'error': f'Erreur: {str(e)}'}, status=500)


@login_required
def scan_history(request):
    """Historique des scans de l'utilisateur"""
    user = request.user
    
    # Récupérer les tickets scannés par l'utilisateur
    scanned_tickets = Ticket.objects.filter(
        used_by=user
    ).select_related(
        'reservation', 
        'reservation__user',
        'reservation__terrain',
        'reservation__activity'
    ).order_by('-used_at')
    
    scans = []
    for ticket in scanned_tickets:
        scans.append({
            'ticket_number': ticket.ticket_number,
            'activity': ticket.reservation.activity.title if ticket.reservation.activity else 'Réservation standard',
            'terrain': ticket.reservation.terrain.name,
            'scanned_at': ticket.used_at.isoformat(),
            'coach': ticket.reservation.user.get_full_name()
        })
    
    return JsonResponse({'scans': scans})


@login_required
def api_documentation(request):
    """Page de documentation de l'API Tickets"""
    return render(request, 'tickets/api_documentation.html')
