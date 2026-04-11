# payments/stripe_service.py
import stripe
from django.conf import settings
from django.urls import reverse
from decimal import Decimal
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

# Configuration Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service pour gérer les paiements Stripe"""
    
    @staticmethod
    def create_checkout_session(reservation, request):
        """
        Crée une session de paiement Stripe pour une réservation
        """
        try:
            # Importer le modèle Payment
            from . import models
            
            # Vérifier si un paiement existe déjà
            payment = models.Payment.objects.filter(reservation=reservation).first()
            if not payment:
                # Créer l'objet Payment en base de données
                payment = models.Payment.objects.create(
                    reservation=reservation,
                    user=reservation.user,
                    amount=reservation.total_amount,
                    currency='XOF',
                    status=models.PaymentStatus.PENDING,
                    payment_method=None,  # Sera mis à jour plus tard
                    notes=f'Paiement Stripe pour réservation {reservation.id}'
                )
            
            # Pour le FCFA (XOF), ne pas multiplier par 100 car pas de décimales
            amount_cents = int(reservation.total_amount)
            
            # URLs de retour
            success_url = request.build_absolute_uri(
                reverse('reservations:payment_success', kwargs={'pk': reservation.id})
            )
            cancel_url = request.build_absolute_uri(
                reverse('reservations:payment_cancel', kwargs={'pk': reservation.id})
            )
            
            # Créer la session de paiement
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'xof',  # Franc CFA
                        'product_data': {
                            'name': f'Réservation {reservation.terrain.name}',
                            'description': f'{reservation.start_time.strftime("%d/%m/%Y %H:%M")} - {reservation.end_time.strftime("%H:%M")}',
                            'images': [],  # Ajouter des images si disponible
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'payment_id': payment.id,
                    'reservation_id': reservation.id,
                    'user_id': reservation.user.id,
                    'terrain_id': reservation.terrain.id,
                    'amount': str(reservation.total_amount),
                },
                customer_email=reservation.user.email,
                billing_address_collection='required',
                shipping_address_collection={
                    'allowed_countries': ['SN', 'CI', 'BF', 'ML', 'NE', 'TG', 'BJ'],  # Pays africains
                }
            )
            
            # Mettre à jour le payment avec l'ID de session Stripe dans les notes
            payment.notes = f'Paiement Stripe pour réservation {reservation.id} - Session: {session.id}'
            payment.save()
            
            logger.info(f"Session Stripe créée: {session.id} pour réservation {reservation.id}, payment {payment.id}")
            
            return {
                'success': True,
                'session_id': session.id,
                'session_url': session.url,
                'amount': reservation.total_amount,
                'currency': 'XOF',
                'payment_id': payment.id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur Stripe création session: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Erreur création session paiement: {str(e)}")
            return {
                'success': False,
                'error': 'Erreur technique lors de la création du paiement'
            }
    
    @staticmethod
    def retrieve_session(session_id):
        """
        Récupère les détails d'une session de paiement
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return {
                'success': True,
                'session': session
            }
        except stripe.error.StripeError as e:
            logger.error(f"Erreur récupération session {session_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def create_payment_intent(reservation, request):
        """
        Crée un Payment Intent pour paiement direct (alternative)
        """
        try:
            # Pour le FCFA (XOF), ne pas multiplier par 100 car pas de décimales
            amount_cents = int(reservation.total_amount)
            
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='xof',
                metadata={
                    'reservation_id': reservation.id,
                    'user_id': reservation.user.id,
                },
                automatic_payment_methods={
                    'enabled': True,
                },
                receipt_email=reservation.user.email,
            )
            
            logger.info(f"Payment Intent créé: {intent.id} pour réservation {reservation.id}")
            
            return {
                'success': True,
                'client_secret': intent.client_secret,
                'intent_id': intent.id,
                'amount': reservation.total_amount
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Erreur Payment Intent: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def confirm_payment_intent(payment_intent_id):
        """
        Confirme un Payment Intent
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                return {
                    'success': True,
                    'status': 'succeeded',
                    'amount': intent.amount / 100,
                    'metadata': intent.metadata
                }
            else:
                return {
                    'success': False,
                    'status': intent.status,
                    'error': 'Paiement non réussi'
                }
                
        except stripe.error.StripeError as e:
            logger.error(f"Erreur confirmation Payment Intent: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def process_webhook(payload, sig_header):
        """
        Traite les webhooks Stripe
        """
        try:
            if not settings.STRIPE_WEBHOOK_SECRET:
                logger.warning("Webhook Secret non configuré")
                return {
                    'success': False,
                    'error': 'Webhook non configuré'
                }
            
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            
            logger.info(f"Webhook Stripe reçu: {event.type}")
            
            # Traiter différents types d'événements
            if event.type == 'checkout.session.completed':
                result = StripeService._handle_checkout_completed(event)
                # Créer la facture après le traitement du paiement
                if result.get('success') and result.get('payment_id'):
                    try:
                        from .models import Payment
                        payment = Payment.objects.get(id=result['payment_id'])
                        from .invoice_service import InvoiceService
                        invoice = InvoiceService.create_invoice_for_payment(payment)
                        if invoice:
                            logger.info(f"Facture {invoice.invoice_number} créée automatiquement après checkout.completed")
                    except Exception as e:
                        logger.error(f"Erreur création facture après checkout: {e}")
                return result
            elif event.type == 'payment_intent.succeeded':
                result = StripeService._handle_payment_succeeded(event)
                # Créer la facture après le traitement du paiement
                if result.get('success') and result.get('reservation_id'):
                    try:
                        from reservations.models import Reservation
                        reservation = Reservation.objects.get(id=result['reservation_id'])
                        from .models import Payment
                        payment = Payment.objects.filter(reservation=reservation).first()
                        if payment:
                            from .invoice_service import InvoiceService
                            invoice = InvoiceService.create_invoice_for_payment(payment)
                            if invoice:
                                logger.info(f"Facture {invoice.invoice_number} créée automatiquement après payment_intent.succeeded")
                    except Exception as e:
                        logger.error(f"Erreur création facture après payment_intent: {e}")
                return result
            elif event.type == 'payment_intent.payment_failed':
                return StripeService._handle_payment_failed(event)
            else:
                logger.info(f"Événement non traité: {event.type}")
                return {
                    'success': True,
                    'message': f'Événement {event.type} reçu mais non traité'
                }
                
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Erreur signature webhook: {str(e)}")
            return {
                'success': False,
                'error': 'Signature webhook invalide'
            }
        except Exception as e:
            logger.error(f"Erreur traitement webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _handle_checkout_completed(event):
        """
        Traite l'événement checkout.session.completed
        """
        session = event.data.object
        
        # Debug: afficher toutes les métadonnées
        logger.info(f"Métadonnées reçues: {session.metadata}")
        logger.info(f"Session ID: {session.id}")
        logger.info(f"Session metadata: {getattr(session, 'metadata', {})}")
        
        reservation_id = session.metadata.get('reservation_id')
        payment_id = session.metadata.get('payment_id')
        
        # Alternative: utiliser payment_id si reservation_id manquant
        if not reservation_id and payment_id:
            logger.info(f"reservation_id manquant, tentative avec payment_id: {payment_id}")
            from . import models
            try:
                payment = models.Payment.objects.get(id=payment_id)
                reservation_id = payment.reservation.id
                logger.info(f"reservation_id trouvé via payment_id: {reservation_id}")
            except models.Payment.DoesNotExist:
                logger.error(f"Payment {payment_id} non trouvé")
                return {
                    'success': False,
                    'error': 'payment non trouvé'
                }
        
        if not reservation_id:
            logger.error(f"reservation_id manquant dans les métadonnées. Métadonnées: {session.metadata}")
            return {
                'success': False,
                'error': 'reservation_id manquant'
            }
        
        try:
            from reservations.models import Reservation
            reservation = Reservation.objects.get(id=reservation_id)
            
            # Mettre à jour le statut du paiement
            from . import models
            payment = models.Payment.objects.filter(reservation=reservation).first()
            if payment:
                payment.status = 'paid'
                payment.paid_at = timezone.now()
                # Ne pas stocker transaction_id pour éviter l'erreur UUID
                # payment.transaction_id = session.payment_intent
                payment.save()
                
                # Si la réservation est confirmée, passer le paiement à completed
                if reservation.status == 'confirmed':
                    payment.status = 'completed'
                    payment.processed_at = timezone.now()
                    payment.save()
                    logger.info(f"Paiement {payment.id} marqué comme completed pour réservation confirmée {reservation_id}")
            else:
                # Créer le paiement s'il n'existe pas
                from . import models
                payment = models.Payment.objects.create(
                    reservation=reservation,
                    amount=session.amount_total / 100,  # Convertir de cents
                    currency=session.currency.upper(),
                    status='paid',
                    paid_at=timezone.now(),
                    # Ne pas stocker transaction_id pour éviter l'erreur UUID
                    # transaction_id=session.payment_intent,
                )
                
                # Si la réservation est déjà confirmée, passer directement à completed
                if reservation.status == 'confirmed':
                    payment.status = 'completed'
                    payment.processed_at = timezone.now()
                    payment.save()
                    logger.info(f"Nouveau paiement {payment.id} marqué comme completed pour réservation confirmée {reservation_id}")
            
            # METTRE À JOUR LE STATUT DE LA RÉSERVATION - C'EST CRUCIAL !
            reservation.payment_status = 'paid'
            reservation.payment_method = 'card'
            reservation.payment_date = timezone.now()
            reservation.transaction_id = session.payment_intent
            reservation.save()
            
            logger.info(f"Paiement réussi pour réservation {reservation_id}")
            logger.info(f"Réservation {reservation_id} mise à jour: payment_status=paid")
            
            # Créer une notification pour les admins
            from payment_notification_service import PaymentNotificationService
            PaymentNotificationService.create_payment_notification(reservation, payment)
            
            return {
                'success': True,
                'message': 'Paiement traité avec succès',
                'reservation_id': reservation_id
            }
            
        except Reservation.DoesNotExist:
            logger.error(f"Réservation {reservation_id} non trouvée")
            return {
                'success': False,
                'error': 'Réservation non trouvée'
            }
    
    @staticmethod
    def _handle_payment_succeeded(event):
        """
        Traite l'événement payment_intent.succeeded
        """
        payment_intent = event.data.object
        reservation_id = payment_intent.metadata.get('reservation_id')
        
        if not reservation_id:
            return {
                'success': False,
                'error': 'reservation_id manquant'
            }
        
        try:
            from reservations.models import Reservation
            reservation = Reservation.objects.get(id=reservation_id)
            
            reservation.payment_status = 'paid'
            reservation.payment_method = 'card'
            reservation.payment_date = timezone.now()
            reservation.transaction_id = payment_intent.id
            reservation.save()
            
            logger.info(f"Payment Intent réussi pour réservation {reservation_id}")
            
            return {
                'success': True,
                'message': 'Paiement traité avec succès',
                'reservation_id': reservation_id
            }
            
        except Reservation.DoesNotExist:
            return {
                'success': False,
                'error': 'Réservation non trouvée'
            }
    
    @staticmethod
    def _handle_payment_failed(event):
        """
        Traite l'événement payment_intent.payment_failed
        """
        payment_intent = event.data.object
        reservation_id = payment_intent.metadata.get('reservation_id')
        
        logger.warning(f"Paiement échoué pour réservation {reservation_id}")
        
        return {
            'success': True,
            'message': 'Paiement échoué',
            'reservation_id': reservation_id
        }
    
    @staticmethod
    def get_payment_methods():
        """
        Retourne les méthodes de paiement disponibles
        """
        return [
            {
                'id': 'card',
                'name': 'Carte bancaire',
                'icon': 'credit-card',
                'description': 'Visa, Mastercard, etc.'
            },
            {
                'id': 'mobile_money',
                'name': 'Mobile Money',
                'icon': 'mobile',
                'description': 'Orange Money, MTN Mobile Money'
            },
            {
                'id': 'bank_transfer',
                'name': 'Virement bancaire',
                'icon': 'university',
                'description': 'Virement direct'
            }
        ]
    
    @staticmethod
    def calculate_fees(amount):
        """
        Calcule les frais de transaction
        """
        # Frais Stripe : 2.9% + 30 cents (pour cartes)
        # Adapter pour le marché africain
        card_fee = amount * Decimal('0.029') + Decimal('0.30')
        mobile_fee = amount * Decimal('0.015')  # 1.5% pour mobile money
        
        return {
            'card': card_fee,
            'mobile_money': mobile_fee,
            'total_with_card_fees': amount + card_fee,
            'total_with_mobile_fees': amount + mobile_fee
        }
