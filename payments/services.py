# payments/services.py
import uuid
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from .models import (
    Payment, PaymentMethod, Transaction, PaymentStatus, 
    PaymentMethodType, Refund, PaymentSubmission, PaymentSubmissionStatus
)
from reservations.models import Reservation


class PaymentSimulationService:
    """Service de simulation de paiement"""
    
    @staticmethod
    def generate_transaction_id():
        """Génère un ID de transaction simulé"""
        return f"SIM-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def generate_otp():
        """Génère un code OTP simulé"""
        return "123456"
    
    @staticmethod
    def simulate_payment_processing(payment_method_type):
        """Simule le temps de traitement selon le moyen de paiement"""
        processing_times = {
            PaymentMethodType.CARD: 2,
            PaymentMethodType.MOBILE_MONEY: 1,
            PaymentMethodType.CASH: 0,
            PaymentMethodType.BANK_TRANSFER: 3,
            PaymentMethodType.WALLET: 1
        }
        return processing_times.get(payment_method_type, 1)
    
    @staticmethod
    def validate_payment_data(payment_method, amount):
        """Valide les données de paiement simulées"""
        errors = []
        
        if not payment_method:
            errors.append("Moyen de paiement requis")
        
        if not amount or amount <= 0:
            errors.append("Montant invalide")
        
        if payment_method and not payment_method.is_active:
            errors.append("Moyen de paiement inactif")
        
        return errors
    
    @classmethod
    def create_payment(cls, reservation, payment_method, amount, notes=""):
        """Crée un paiement simulé"""
        # Validation
        errors = cls.validate_payment_data(payment_method, amount)
        if errors:
            raise ValueError(f"Erreur de validation: {', '.join(errors)}")
        
        # Création du paiement
        payment = Payment.objects.create(
            reservation=reservation,
            user=reservation.user,
            amount=amount,
            payment_method=payment_method,
            notes=notes,
            is_simulated=True
        )
        
        # Création de la transaction simulée
        transaction_obj = Transaction.objects.create(
            transaction_id=cls.generate_transaction_id(),
            amount=amount,
            status=PaymentStatus.SIMULATED,
            payment_method=payment_method,
            gateway_response={
                'simulated': True,
                'processing_time': cls.simulate_payment_processing(payment_method.method_type),
                'otp': cls.generate_otp(),
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Lier la transaction au paiement
        payment.transaction = transaction_obj
        payment.status = PaymentStatus.SIMULATED
        payment.paid_at = timezone.now()
        payment.simulation_data = {
            'otp': cls.generate_otp(),
            'processing_time': cls.simulate_payment_processing(payment_method.method_type),
            'gateway': f"{payment_method.provider} (Simulé)",
            'authorized_at': timezone.now().isoformat()
        }
        payment.save()
        
        # Mettre à jour le statut de la réservation
        reservation.status = 'confirmed'
        reservation.save()
        
        # Envoyer notification
        cls._send_payment_notification(payment, 'simulated')
        
        return payment
    
    @staticmethod
    def _send_payment_notification(payment, payment_type):
        """Envoie une notification de paiement"""
        try:
            from notifications.utils import NotificationService
            
            title = "Paiement simulé effectué"
            message = f"Votre paiement de {payment.amount} {payment.currency} pour la réservation #{payment.reservation.id} a été simulé avec succès."
            
            NotificationService.create_notification(
                recipient=payment.user,
                title=title,
                message=message,
                notification_type='payment_simulated',
                content_object=payment
            )
        except Exception as e:
            print(f"Erreur notification: {e}")


class PaymentService:
    """Service principal de gestion des paiements"""
    
    @staticmethod
    def create_payment_from_reservation(reservation, payment_method_id=None, notes=""):
        """Crée un paiement à partir d'une réservation"""
        # Calcul du montant
        amount = PaymentService._calculate_reservation_amount(reservation)
        
        # Récupération du moyen de paiement
        payment_method = None
        if payment_method_id:
            try:
                payment_method = PaymentMethod.objects.get(
                    id=payment_method_id, 
                    user=reservation.user, 
                    is_active=True
                )
            except PaymentMethod.DoesNotExist:
                raise ValueError("Moyen de paiement invalide")
        
        # Création du paiement simulé
        return PaymentSimulationService.create_payment(
            reservation, payment_method, amount, notes
        )
    
    @staticmethod
    def _calculate_reservation_amount(reservation):
        """Calcule le montant de la réservation"""
        # Durée en heures
        duration = reservation.end_time - reservation.start_time
        hours = duration.total_seconds() / 3600
        
        # Prix par heure du terrain
        price_per_hour = reservation.terrain.price_per_hour
        
        # Calcul du montant total
        amount = Decimal(str(hours)) * price_per_hour
        
        return amount.quantize(Decimal('0.01'))
    
    @staticmethod
    def get_user_payment_methods(user):
        """Récupère les moyens de paiement d'un utilisateur"""
        return PaymentMethod.objects.filter(
            user=user, 
            is_active=True
        ).order_by('-is_default')
    
    @staticmethod
    def add_payment_method(user, method_type, provider, identifier, display_name):
        """Ajoute un moyen de paiement pour un utilisateur"""
        # Vérifier si c'est le premier moyen de paiement
        is_first = not PaymentMethod.objects.filter(user=user).exists()
        
        payment_method = PaymentMethod.objects.create(
            user=user,
            method_type=method_type,
            provider=provider,
            identifier=identifier,
            display_name=display_name,
            is_default=is_first,
            is_verified=True  # Auto-vérifié en mode simulation
        )
        
        return payment_method
    
    @staticmethod
    def set_default_payment_method(user, payment_method_id):
        """Définit le moyen de paiement par défaut"""
        # Désactiver tous les autres
        PaymentMethod.objects.filter(user=user).update(is_default=False)
        
        # Activer celui choisi
        try:
            payment_method = PaymentMethod.objects.get(
                id=payment_method_id, 
                user=user
            )
            payment_method.is_default = True
            payment_method.save()
            return payment_method
        except PaymentMethod.DoesNotExist:
            raise ValueError("Moyen de paiement introuvable")
    
    @staticmethod
    def get_payment_statistics(user=None, start_date=None, end_date=None):
        """Récupère les statistiques de paiement"""
        queryset = Payment.objects.all()
        
        if user:
            queryset = queryset.filter(user=user)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        stats = {
            'total_payments': queryset.count(),
            'total_amount': queryset.aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0'),
            'simulated_payments': queryset.filter(is_simulated=True).count(),
            'real_payments': queryset.filter(is_simulated=False).count(),
            'successful_payments': queryset.filter(
                status__in=[PaymentStatus.COMPLETED, PaymentStatus.SIMULATED]
            ).count(),
            'failed_payments': queryset.filter(status=PaymentStatus.FAILED).count(),
        }
        
        return stats


class RefundService:
    """Service de gestion des remboursements"""
    
    @staticmethod
    def create_refund(payment, amount, reason, processed_by=None):
        """Crée un remboursement"""
        if not payment.can_be_refunded:
            raise ValueError("Ce paiement ne peut pas être remboursé")
        
        if amount > payment.amount:
            raise ValueError("Le montant du remboursement ne peut pas dépasser le montant du paiement")
        
        with transaction.atomic():
            # Créer le remboursement
            refund = Refund.objects.create(
                payment=payment,
                amount=amount,
                reason=reason,
                processed_by=processed_by,
                status=PaymentStatus.SIMULATED if payment.is_simulated else PaymentStatus.PENDING
            )
            
            # Créer la transaction de remboursement simulée
            if payment.is_simulated:
                refund_transaction = Transaction.objects.create(
                    transaction_id=f"REF-SIM-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                    amount=amount,
                    status=PaymentStatus.SIMULATED,
                    gateway_response={
                        'simulated': True,
                        'refund_type': 'simulated',
                        'timestamp': timezone.now().isoformat()
                    }
                )
                refund.refund_transaction = refund_transaction
                refund.status = PaymentStatus.SIMULATED
                refund.save()
            
            return refund
    
    @staticmethod
    def process_refund(refund_id, processed_by):
        """Traite un remboursement"""
        try:
            refund = Refund.objects.get(id=refund_id)
        except Refund.DoesNotExist:
            raise ValueError("Remboursement introuvable")
        
        if refund.status == PaymentStatus.COMPLETED:
            raise ValueError("Remboursement déjà traité")
        
        # Simulation du traitement
        refund.status = PaymentStatus.COMPLETED
        refund.processed_by = processed_by
        refund.save()
        
        # Mettre à jour le statut du paiement
        payment = refund.payment
        if refund.amount >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
        payment.save()
        
        return refund


class PaymentSubmissionService:
    """Service de gestion des soumissions de paiement manuel"""
    
    @staticmethod
    def create_payment_submission(reservation, payment_data, request=None):
        """Crée une soumission de paiement"""
        # Validation
        if reservation.has_payment:
            raise ValueError("Cette réservation a déjà un paiement")
        
        if reservation.has_payment_submission:
            raise ValueError("Cette réservation a déjà une soumission de paiement")
        
        # Extraction des données de paiement
        payment_method_type = payment_data.get('payment_method_type')
        amount_str = payment_data.get('amount', reservation.total_amount)
        # Remplacer la virgule par un point pour le format décimal
        amount_str = str(amount_str).replace(',', '.')
        amount = Decimal(amount_str)
        
        # Validation des données
        if not payment_method_type:
            raise ValueError("Type de paiement requis")
        
        if amount <= 0:
            raise ValueError("Montant invalide")
        
        # Création de la soumission
        submission_data = {
            'payment_method_type': payment_method_type,
            'amount': amount,
            'currency': 'XOF',
            'notes': payment_data.get('notes', ''),
        }
        
        # Ajouter les détails spécifiques selon le type de paiement
        if payment_method_type == PaymentMethodType.CARD:
            card_number = payment_data.get('card_number', '')
            submission_data.update({
                'card_last_four': card_number[-4:] if len(card_number) >= 4 else '',
                'card_holder_name': payment_data.get('card_holder_name', ''),
                'payment_details': {
                    'card_type': payment_data.get('card_type', 'unknown'),
                    'expiry': payment_data.get('expiry', ''),
                }
            })
        elif payment_method_type == PaymentMethodType.MOBILE_MONEY:
            mobile_number = payment_data.get('mobile_number', '')
            submission_data.update({
                'mobile_number': mobile_number,
                'mobile_provider': payment_data.get('mobile_provider', ''),
                'payment_details': {
                    'provider': payment_data.get('mobile_provider', ''),
                }
            })
        
        # Ajouter les informations de requête
        if request:
            submission_data.update({
                'submission_ip': PaymentSubmissionService._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            })
        
        # Créer la soumission
        submission = PaymentSubmission.objects.create(
            reservation=reservation,
            user=reservation.user,
            **submission_data
        )
        
        # Envoyer notification à l'administrateur
        PaymentSubmissionService._notify_admin_payment_submission(submission)
        
        # Envoyer confirmation à l'utilisateur
        PaymentSubmissionService._notify_user_submission_received(submission)
        
        return submission
    
    @staticmethod
    def validate_payment_submission(submission_id, admin_user, notes=""):
        """Valide une soumission de paiement"""
        try:
            submission = PaymentSubmission.objects.get(id=submission_id)
        except PaymentSubmission.DoesNotExist:
            raise ValueError("Soumission introuvable")
        
        if not submission.is_pending_validation:
            raise ValueError("Cette soumission n'est pas en attente de validation")
        
        try:
            print(f"Avant validation - submission status: {submission.status}")
            
            # Valider la soumission
            payment = submission.validate_submission(admin_user, notes)
            print(f"Après validation - submission status: {submission.status}")
            print(f"Payment créé: {payment.id}")
            
            # Mettre à jour le statut de la réservation
            submission.reservation.status = 'confirmed'
            submission.reservation.save()
            print(f"Réservation status mis à jour: {submission.reservation.status}")
            
            # Envoyer notification de validation à l'utilisateur
            try:
                PaymentSubmissionService._notify_user_payment_validated(submission, payment)
            except Exception as e:
                print(f"Erreur notification validation: {e}")
                # Continuer même si la notification échoue
            
            return payment
            
        except Exception as e:
            print(f"Erreur validation: {e}")
            raise
    
    @staticmethod
    def reject_payment_submission(submission_id, admin_user, reason=""):
        """Rejette une soumission de paiement"""
        try:
            submission = PaymentSubmission.objects.get(id=submission_id)
        except PaymentSubmission.DoesNotExist:
            raise ValueError("Soumission introuvable")
        
        if not submission.is_pending_validation:
            raise ValueError("Cette soumission n'est pas en attente de validation")
        
        with transaction.atomic():
            # Rejeter la soumission
            submission.reject_submission(admin_user, reason)
            
            # Mettre à jour le statut de la réservation
            submission.reservation.status = 'pending'
            submission.reservation.save()
            
            # Envoyer notification de rejet à l'utilisateur
            # PaymentSubmissionService._notify_user_payment_rejected(submission, reason)  # Désactivé temporairement à cause de l'erreur UUID
            
            return submission
    
    @staticmethod
    def get_pending_submissions():
        """Récupère toutes les soumissions en attente de validation"""
        return PaymentSubmission.objects.filter(
            status__in=[PaymentSubmissionStatus.SUBMITTED, PaymentSubmissionStatus.UNDER_REVIEW]
        ).order_by('-created_at')
    
    @staticmethod
    def get_submission_statistics():
        """Récupère les statistiques des soumissions"""
        total = PaymentSubmission.objects.count()
        pending = PaymentSubmission.objects.filter(
            status__in=[PaymentSubmissionStatus.SUBMITTED, PaymentSubmissionStatus.UNDER_REVIEW]
        ).count()
        validated = PaymentSubmission.objects.filter(
            status=PaymentSubmissionStatus.VALIDATED
        ).count()
        rejected = PaymentSubmission.objects.filter(
            status=PaymentSubmissionStatus.REJECTED
        ).count()
        
        return {
            'total': total,
            'pending': pending,
            'validated': validated,
            'rejected': rejected,
            'validation_rate': (validated / total * 100) if total > 0 else 0,
        }
    
    @staticmethod
    def _get_client_ip(request):
        """Récupère l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def _notify_admin_payment_submission(submission):
        """Notifie les administrateurs d'une nouvelle soumission"""
        try:
            from notifications.utils import NotificationService
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            admins = User.objects.filter(role='admin')
            
            title = "Nouvelle soumission de paiement"
            message = f"Une nouvelle soumission de paiement de {submission.amount} {submission.currency} est en attente de validation pour la réservation #{submission.reservation.id}."
            
            for admin in admins:
                NotificationService.create_notification(
                    recipient=admin,
                    title=title,
                    message=message,
                    notification_type='payment_submission',
                    content_object=submission
                )
        except Exception as e:
            print(f"Erreur notification admin: {e}")
    
    @staticmethod
    def _notify_user_submission_received(submission):
        """Notifie l'utilisateur que sa soumission a été reçue"""
        try:
            from notifications.utils import NotificationService
            
            title = "Soumission de paiement reçue"
            message = f"Votre soumission de paiement de {submission.amount} {submission.currency} pour la réservation #{submission.reservation.id} a été reçue et est en cours de validation."
            
            NotificationService.create_notification(
                recipient=submission.user,
                title=title,
                message=message,
                notification_type='payment_submission_received',
                content_object=submission
            )
        except Exception as e:
            print(f"Erreur notification utilisateur: {e}")
    
    @staticmethod
    def _notify_user_payment_validated(submission, payment):
        """Notifie l'utilisateur que son paiement a été validé"""
        try:
            from notifications.utils import NotificationService
            
            title = "Paiement validé"
            message = f"Votre paiement de {payment.amount} {payment.currency} pour la réservation #{submission.reservation.id} a été validé avec succès. Votre réservation est maintenant confirmée."
            
            NotificationService.create_notification(
                recipient=submission.user,
                title=title,
                message=message,
                notification_type='payment_validated',
                content_object=payment
            )
        except Exception as e:
            print(f"Erreur notification validation: {e}")
    
    @staticmethod
    def _notify_user_payment_rejected(submission, reason):
        """Notifie l'utilisateur que son paiement a été rejeté"""
        try:
            from notifications.utils import NotificationService
            
            title = "Paiement rejeté"
            message = f"Votre soumission de paiement pour la réservation #{submission.reservation.id} a été rejetée. Raison: {reason}"
            
            NotificationService.create_notification(
                recipient=submission.user,
                title=title,
                message=message,
                notification_type='payment_rejected',
                content_object=submission
            )
        except Exception as e:
            print(f"Erreur notification rejet: {e}")
