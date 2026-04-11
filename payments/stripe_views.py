# payments/stripe_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
import json
import logging
import sys
from logging import StreamHandler

from reservations.models import Reservation
from .stripe_service import StripeService
from .models import Payment
from .invoice_service import InvoiceService

# Configuration du logger pour éviter les problèmes colorama sur Windows
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@login_required
def stripe_payment_checkout(request, reservation_id):
    """
    Page de paiement Stripe pour une réservation
    """
    logger.info(f"=== STRIPE PAYMENT CHECKOUT pour réservation {reservation_id} ===")
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifications
    if reservation.user != request.user and request.user.role != 'admin':
        messages.error(request, 'Non autorisé à payer cette réservation.')
        return redirect('reservations:reservation_detail', pk=reservation_id)
    
    if reservation.payment_status == 'paid':
        messages.info(request, 'Cette réservation est déjà payée.')
        return redirect('reservations:reservation_detail', pk=reservation_id)
    
    # Créer la session Stripe
    result = StripeService.create_checkout_session(reservation, request)
    
    if not result['success']:
        messages.error(request, f"Erreur lors de la création du paiement: {result['error']}")
        return redirect('reservations:payment_checkout', pk=reservation_id)
    
    # Rediriger vers Stripe Checkout
    return redirect(result['session_url'])


@login_required
def stripe_payment_success(request, reservation_id):
    """
    Page de succès après paiement Stripe
    """
    logger.info(f"=== STRIPE PAYMENT SUCCESS pour réservation {reservation_id} ===")
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifier si le paiement a été traité
    if reservation.payment_status == 'paid':
        messages.success(request, 'Paiement effectué avec succès! Votre réservation est confirmée.')
    else:
        # Le webhook peut prendre quelques secondes
        messages.info(request, 'Votre paiement est en cours de validation. Vous recevrez une confirmation shortly.')
    
    return redirect('reservations:reservation_detail', pk=reservation_id)


@login_required
def stripe_payment_cancel(request, reservation_id):
    """
    Page d'annulation de paiement Stripe
    """
    logger.info(f"=== STRIPE PAYMENT CANCEL pour réservation {reservation_id} ===")
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    messages.warning(request, 'Paiement annulé. Vous pouvez réessayer plus tard.')
    
    return redirect('reservations:payment_checkout', pk=reservation_id)


@login_required
def stripe_payment_intent(request, reservation_id):
    """
    Crée un Payment Intent pour paiement direct (JavaScript)
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérifications
    if reservation.user != request.user and request.user.role != 'admin':
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    if reservation.payment_status == 'paid':
        return JsonResponse({'error': 'Déjà payé'}, status=400)
    
    # Créer le Payment Intent
    result = StripeService.create_payment_intent(reservation, request)
    
    if result['success']:
        return JsonResponse({
            'success': True,
            'client_secret': result['client_secret'],
            'amount': result['amount']
        })
    else:
        return JsonResponse({'error': result['error']}, status=400)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Webhook Stripe pour traiter les événements de paiement
    """
    logger.info(f"=== STRIPE WEBHOOK REÇU ===")
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    # Traiter le webhook
    result = StripeService.process_webhook(payload, sig_header)
    
    if result['success']:
        # Créer automatiquement la facture si le paiement est réussi
        if result.get('event_type') == 'payment_intent.succeeded':
            payment_id = result.get('payment_id')
            if payment_id:
                try:
                    payment = Payment.objects.get(id=payment_id)
                    invoice = InvoiceService.create_invoice_for_payment(payment)
                    if invoice:
                        logger.info(f"Facture {invoice.invoice_number} créée automatiquement pour le paiement {payment_id}")
                    else:
                        logger.warning(f"Facture déjà existante pour le paiement {payment_id}")
                except Payment.DoesNotExist:
                    logger.error(f"Paiement {payment_id} non trouvé pour créer la facture")
                except Exception as e:
                    logger.error(f"Erreur lors de la création automatique de la facture: {e}")
        
        return HttpResponse(status=200)
    else:
        return JsonResponse({'error': result['error']}, status=400)


@login_required
def stripe_payment_methods(request):
    """
    API pour obtenir les méthodes de paiement disponibles
    """
    methods = StripeService.get_payment_methods()
    return JsonResponse({'methods': methods})


@login_required
def stripe_calculate_fees(request):
    """
    API pour calculer les frais de transaction
    """
    try:
        amount = float(request.GET.get('amount', 0))
        from decimal import Decimal
        amount_decimal = Decimal(str(amount))
        
        fees = StripeService.calculate_fees(amount_decimal)
        
        return JsonResponse({
            'success': True,
            'fees': {
                'card': float(fees['card']),
                'mobile_money': float(fees['mobile_money']),
                'total_with_card_fees': float(fees['total_with_card_fees']),
                'total_with_mobile_fees': float(fees['total_with_mobile_fees'])
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def stripe_payment_status(request, reservation_id):
    """
    API pour vérifier le statut de paiement d'une réservation
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.user != request.user and request.user.role != 'admin':
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    return JsonResponse({
        'success': True,
        'payment_status': reservation.payment_status,
        'payment_method': reservation.payment_method,
        'payment_date': reservation.payment_date.isoformat() if reservation.payment_date else None,
        'transaction_id': reservation.transaction_id,
        'total_amount': float(reservation.total_amount)
    })


@login_required
def stripe_refund_payment(request, reservation_id):
    """
    API pour rembourser un paiement (admin uniquement)
    """
    if request.user.role != 'admin':
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if reservation.payment_status != 'paid':
        return JsonResponse({'error': 'Aucun paiement à rembourser'}, status=400)
    
    try:
        # Rembourser via Stripe
        if reservation.transaction_id:
            refund = stripe.Refund.create(
                payment_intent=reservation.transaction_id,
                reason='requested_by_customer'
            )
            
            # Mettre à jour le statut
            reservation.payment_status = 'refunded'
            reservation.save()
            
            logger.info(f"Remboursement effectué pour réservation {reservation_id}")
            
            return JsonResponse({
                'success': True,
                'refund_id': refund.id,
                'amount': refund.amount / 100
            })
        else:
            return JsonResponse({'error': 'Aucun ID de transaction trouvé'}, status=400)
            
    except stripe.error.StripeError as e:
        logger.error(f"Erreur remboursement: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def stripe_payment_history(request):
    """
    API pour obtenir l'historique des paiements de l'utilisateur
    """
    user = request.user
    
    reservations = Reservation.objects.filter(
        user=user,
        payment_status__in=['paid', 'refunded']
    ).order_by('-payment_date')
    
    payments = []
    for reservation in reservations:
        payments.append({
            'reservation_id': reservation.id,
            'amount': float(reservation.total_amount),
            'payment_status': reservation.payment_status,
            'payment_method': reservation.payment_method,
            'payment_date': reservation.payment_date.isoformat() if reservation.payment_date else None,
            'transaction_id': reservation.transaction_id,
            'terrain': reservation.terrain.name,
            'start_time': reservation.start_time.isoformat()
        })
    
    return JsonResponse({'payments': payments})
