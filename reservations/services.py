# reservations/services.py - Services d'orchestration des réservations
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List
import logging

from .models import Reservation, ReservationStatus
from terrains.models import Terrain
from timeslots.models import TimeSlot, TimeSlotStatus
from pricing.services import DynamicPricingService
from payments.models import Payment, PaymentStatus
from subscriptions.models import Subscription, UserCredit
from waitinglist.models import WaitingList, WaitingListStatus
from notifications.utils import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)


class ReservationOrchestrationService:
    """Service central d'orchestration des réservations"""
    
    @staticmethod
    @transaction.atomic
    def create_complete_reservation(
        user: User,
        terrain: Terrain,
        start_datetime: datetime,
        end_datetime: datetime,
        notes: str = "",
        payment_method_id: Optional[str] = None,
        use_subscription: bool = False,
        use_credits: bool = False
    ) -> Dict:
        """
        Crée une réservation complète avec tous les modules connectés
        Workflow: Vérification → Tarification → Création → Paiement → Confirmation
        """
        try:
            # 1. Vérification de disponibilité
            is_available, conflict_details = TimeSlotService.check_availability(
                terrain, start_datetime, end_datetime
            )
            
            if not is_available:
                # Ajouter à la liste d'attente si souhaité
                waiting_result = WaitingListService.add_to_waiting_list(
                    user, terrain, start_datetime, end_datetime
                )
                return {
                    "success": False,
                    "error": "Créneau non disponible",
                    "conflicts": conflict_details,
                    "waiting_list": waiting_result
                }
            
            # 2. Calcul du prix avec tarification dynamique
            pricing_result = DynamicPricingService.calculate_price(
                terrain=terrain,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                user=user
            )
            
            base_price = pricing_result['base_price']
            final_price = pricing_result['final_price']
            applied_rules = pricing_result['applied_rules']
            
            # 3. Vérification des abonnements/crédits
            discount = Decimal('0')
            subscription_used = None
            credits_used = Decimal('0')
            
            if use_subscription:
                sub_result = SubscriptionService.get_best_subscription(user, terrain)
                if sub_result['success']:
                    discount = sub_result['discount']
                    subscription_used = sub_result['subscription']
                    final_price -= discount
            
            if use_credits and final_price > 0:
                credit_result = CreditService.use_available_credits(user, final_price)
                if credit_result['success']:
                    credits_used = credit_result['credits_used']
                    final_price -= credits_used
            
            # 4. Création de la réservation
            reservation = Reservation.objects.create(
                user=user,
                terrain=terrain,
                start_time=start_datetime,
                end_time=end_datetime,
                notes=notes,
                status=ReservationStatus.PENDING
            )
            
            # 5. Réservation et blocage du TimeSlot
            timeslot = TimeSlotService.reserve_timeslot(
                terrain, start_datetime, end_datetime, reservation
            )
            
            # 6. Création du paiement si nécessaire
            payment = None
            if final_price > 0:
                payment = PaymentService.create_payment(
                    reservation=reservation,
                    user=user,
                    amount=final_price,
                    payment_method_id=payment_method_id
                )
            else:
                # Réservation gratuite, confirmer automatiquement
                reservation.status = ReservationStatus.CONFIRMED
                reservation.save()
            
            # 7. Enregistrement de l'historique de prix
            PriceHistoryService.record_price_history(
                terrain=terrain,
                reservation=reservation,
                user=user,
                base_price=base_price,
                final_price=final_price,
                applied_rules=applied_rules,
                discount=discount + credits_used
            )
            
            # 8. Mise à jour des abonnements/crédits utilisés
            if subscription_used:
                SubscriptionService.record_reservation_usage(
                    subscription_used, 
                    (end_datetime - start_datetime).total_seconds() / 3600
                )
            
            # 9. Notifications
            NotificationService.create_notification(
                recipient=user,
                title="Réservation créée",
                message=f"Votre réservation du terrain {terrain.name} pour le {start_datetime.strftime('%d/%m/%Y à %H:%M')} a été créée.",
                notification_type='reservation_created',
                content_object=reservation
            )
            
            # Notification aux admins
            admins = User.objects.filter(role='admin')
            for admin in admins:
                NotificationService.create_notification(
                    recipient=admin,
                    title="Nouvelle réservation",
                    message=f"Nouvelle réservation de {user.get_full_name()} - Terrain {terrain.name}",
                    notification_type='new_reservation',
                    content_object=reservation
                )
            
            return {
                "success": True,
                "reservation": reservation,
                "timeslot": timeslot,
                "payment": payment,
                "pricing": {
                    "base_price": base_price,
                    "final_price": final_price,
                    "discount": discount + credits_used,
                    "applied_rules": applied_rules
                },
                "subscription": subscription_used,
                "credits_used": credits_used
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de réservation: {str(e)}")
            return {
                "success": False,
                "error": f"Erreur technique: {str(e)}"
            }
    
    @staticmethod
    @transaction.atomic
    def cancel_reservation(reservation: Reservation, cancelled_by: User, reason: str = "") -> Dict:
        """
        Annule une réservation et libère les ressources
        """
        try:
            # 1. Vérifier si l'annulation est possible
            if reservation.status in [ReservationStatus.COMPLETED, ReservationStatus.CANCELLED]:
                return {
                    "success": False,
                    "error": "Cette réservation ne peut plus être annulée"
                }
            
            # 2. Remboursement si paiement effectué
            refund_amount = Decimal('0')
            if hasattr(reservation, 'payment') and reservation.payment.is_paid:
                refund_result = PaymentService.process_refund(
                    reservation.payment, 
                    reason or "Annulation de réservation"
                )
                if refund_result['success']:
                    refund_amount = refund_result['refund_amount']
            
            # 3. Libération du TimeSlot
            if hasattr(reservation, 'timeslot'):
                TimeSlotService.release_timeslot(reservation.timeslot)
            
            # 4. Mise à jour du statut
            reservation.status = ReservationStatus.CANCELLED
            reservation.save()
            
            # 5. Notification à la liste d'attente
            waiting_result = WaitingListService.notify_waiting_list(
                reservation.terrain,
                reservation.start_time,
                reservation.end_time
            )
            
            # 6. Notifications
            NotificationService.create_notification(
                recipient=reservation.user,
                title="Réservation annulée",
                message=f"Votre réservation du terrain {reservation.terrain.name} a été annulée.",
                notification_type='reservation_cancelled',
                content_object=reservation
            )
            
            return {
                "success": True,
                "refund_amount": refund_amount,
                "waiting_list_notified": waiting_result['notified_count']
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de réservation: {str(e)}")
            return {
                "success": False,
                "error": f"Erreur technique: {str(e)}"
            }
    
    @staticmethod
    def get_reservation_details(reservation_id: int) -> Dict:
        """
        Récupère tous les détails d'une réservation avec les modules connectés
        """
        try:
            reservation = Reservation.objects.get(id=reservation_id)
            
            details = {
                "reservation": reservation,
                "timeslot": getattr(reservation, 'timeslot', None),
                "payment": getattr(reservation, 'payment', None),
                "price_history": reservation.price_history.first() if hasattr(reservation, 'price_history') else None,
                "subscription": None,
                "user_credits": [],
                "waiting_list_entry": getattr(reservation, 'waiting_list_entry', None)
            }
            
            # Récupérer l'abonnement actif de l'utilisateur
            active_subscription = Subscription.objects.filter(
                user=reservation.user,
                status='active',
                end_date__gt=timezone.now()
            ).first()
            
            if active_subscription:
                details["subscription"] = active_subscription
            
            # Récupérer les crédits de l'utilisateur
            user_credits = UserCredit.objects.filter(
                user=reservation.user,
                is_active=True
            ).order_by('-expires_at')
            
            details["user_credits"] = user_credits
            
            return {
                "success": True,
                "details": details
            }
            
        except Reservation.DoesNotExist:
            return {
                "success": False,
                "error": "Réservation non trouvée"
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des détails: {str(e)}")
            return {
                "success": False,
                "error": f"Erreur technique: {str(e)}"
            }


class TimeSlotService:
    """Service pour la gestion des créneaux horaires"""
    
    @staticmethod
    def check_availability(terrain: Terrain, start_datetime: datetime, end_datetime: datetime) -> Tuple[bool, List]:
        """Vérifie la disponibilité d'un créneau"""
        conflicting_slots = TimeSlot.objects.filter(
            terrain=terrain,
            date=start_datetime.date(),
            start_time__lt=end_datetime.time(),
            end_time__gt=start_datetime.time(),
            status=TimeSlotStatus.BOOKED
        )
        
        is_available = conflicting_slots.count() == 0
        return is_available, list(conflicting_slots)
    
    @staticmethod
    def reserve_timeslot(terrain: Terrain, start_datetime: datetime, end_datetime: datetime, reservation: Reservation) -> TimeSlot:
        """Réserve un créneau horaire"""
        timeslot, created = TimeSlot.objects.get_or_create(
            terrain=terrain,
            date=start_datetime.date(),
            start_time=start_datetime.time(),
            end_time=end_datetime.time(),
            defaults={
                'status': TimeSlotStatus.BOOKED,
                'reservation': reservation
            }
        )
        
        if not created:
            timeslot.status = TimeSlotStatus.BOOKED
            timeslot.reservation = reservation
            timeslot.save()
        
        return timeslot
    
    @staticmethod
    def release_timeslot(timeslot: TimeSlot):
        """Libère un créneau horaire"""
        timeslot.status = TimeSlotStatus.AVAILABLE
        timeslot.reservation = None
        timeslot.save()


class PaymentService:
    """Service pour la gestion des paiements"""
    
    @staticmethod
    def create_payment(reservation: Reservation, user: User, amount: Decimal, payment_method_id: Optional[str] = None) -> Payment:
        """Crée un paiement pour une réservation"""
        payment = Payment.objects.create(
            reservation=reservation,
            user=user,
            amount=amount,
            status=PaymentStatus.PENDING
        )
        
        # Simulation de paiement automatique pour le développement
        payment.status = PaymentStatus.SIMULATED
        payment.is_simulated = True
        payment.paid_at = timezone.now()
        payment.save()
        
        # Confirmer la réservation après paiement
        reservation.status = ReservationStatus.CONFIRMED
        reservation.save()
        
        return payment
    
    @staticmethod
    def process_refund(payment: Payment, reason: str) -> Dict:
        """Traite un remboursement"""
        try:
            from payments.models import Refund
            
            refund = Refund.objects.create(
                payment=payment,
                amount=payment.amount,
                reason=reason,
                status=PaymentStatus.COMPLETED,
                processed_by=User.objects.filter(role='admin').first()
            )
            
            return {
                "success": True,
                "refund_amount": payment.amount,
                "refund": refund
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class SubscriptionService:
    """Service pour la gestion des abonnements"""
    
    @staticmethod
    def get_best_subscription(user: User, terrain: Terrain) -> Dict:
        """Récupère le meilleur abonnement pour l'utilisateur"""
        active_subscriptions = Subscription.objects.filter(
            user=user,
            status='active',
            end_date__gt=timezone.now()
        ).select_related('membership')
        
        best_subscription = None
        max_discount = Decimal('0')
        
        for subscription in active_subscriptions:
            # Vérifier si le terrain est autorisé
            if (subscription.membership.allowed_terrains.exists() and 
                terrain not in subscription.membership.allowed_terrains.all()):
                continue
            
            # Vérifier si l'utilisateur peut faire une réservation
            can_reserve, reason = subscription.can_make_reservation
            if not can_reserve:
                continue
            
            discount = subscription.membership.discount_percentage
            if discount > max_discount:
                max_discount = discount
                best_subscription = subscription
        
        if best_subscription:
            return {
                "success": True,
                "subscription": best_subscription,
                "discount": max_discount
            }
        
        return {
            "success": False,
            "error": "Aucun abonnement applicable"
        }
    
    @staticmethod
    def record_reservation_usage(subscription: Subscription, duration_hours: float):
        """Enregistre l'utilisation d'une réservation"""
        subscription.record_reservation_usage(Decimal(str(duration_hours)))


class CreditService:
    """Service pour la gestion des crédits"""
    
    @staticmethod
    def use_available_credits(user: User, amount_needed: Decimal) -> Dict:
        """Utilise les crédits disponibles de l'utilisateur"""
        available_credits = UserCredit.objects.filter(
            user=user,
            is_active=True,
            amount__gt=0
        ).order_by('expires_at')
        
        total_available = sum(credit.amount for credit in available_credits)
        
        if total_available < amount_needed:
            return {
                "success": False,
                "error": "Crédits insuffisants",
                "available": total_available,
                "needed": amount_needed
            }
        
        # Utiliser les crédits par ordre d'expiration
        amount_to_use = amount_needed
        used_credits = []
        
        for credit in available_credits:
            if amount_to_use <= 0:
                break
            
            use_amount = min(credit.amount, amount_to_use)
            if credit.use_credits(use_amount):
                used_credits.append({
                    "credit": credit,
                    "amount": use_amount
                })
                amount_to_use -= use_amount
        
        return {
            "success": True,
            "credits_used": amount_needed - amount_to_use,
            "used_credits": used_credits
        }


class WaitingListService:
    """Service pour la gestion de la liste d'attente"""
    
    @staticmethod
    def add_to_waiting_list(user: User, terrain: Terrain, start_datetime: datetime, end_datetime: datetime) -> Dict:
        """Ajoute un utilisateur à la liste d'attente"""
        try:
            waiting_entry, created = WaitingList.objects.get_or_create(
                user=user,
                terrain=terrain,
                date=start_datetime.date(),
                start_time=start_datetime.time(),
                end_time=end_datetime.time(),
                defaults={
                    'duration_minutes': int((end_datetime - start_datetime).total_seconds() / 60),
                    'status': WaitingListStatus.WAITING
                }
            )
            
            if created:
                return {
                    "success": True,
                    "message": "Ajouté à la liste d'attente",
                    "position": WaitingList.objects.filter(
                        terrain=terrain,
                        date=start_datetime.date(),
                        status=WaitingListStatus.WAITING
                    ).count()
                }
            else:
                return {
                    "success": False,
                    "error": "Déjà dans la liste d'attente"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def notify_waiting_list(terrain: Terrain, start_datetime: datetime, end_datetime: datetime) -> Dict:
        """Notifie la liste d'attente pour un créneau disponible"""
        waiting_entries = WaitingList.objects.filter(
            terrain=terrain,
            date=start_datetime.date(),
            status=WaitingListStatus.WAITING
        ).order_by('priority', 'created_at')
        
        notified_count = 0
        
        for entry in waiting_entries:
            if entry.can_match_timeslot(type('MockTimeSlot', (), {
                'date': start_datetime.date(),
                'start_time': start_datetime.time(),
                'end_time': end_datetime.time(),
                'duration_minutes': int((end_datetime - start_datetime).total_seconds() / 60)
            })()):
                entry.notify_user()
                notified_count += 1
                break  # Notifier seulement le premier
        
        return {
            "success": True,
            "notified_count": notified_count
        }


class PriceHistoryService:
    """Service pour l'historique des prix"""
    
    @staticmethod
    def record_price_history(terrain: Terrain, reservation: Reservation, user: User, 
                           base_price: Decimal, final_price: Decimal, 
                           applied_rules: List, discount: Decimal):
        """Enregistre l'historique des prix"""
        from pricing.models import PriceHistory
        
        PriceHistory.objects.create(
            terrain=terrain,
            reservation=reservation,
            base_price=base_price,
            final_price=final_price,
            applied_rules=applied_rules,
            price_adjustments={"discount": discount},
            user=user
        )
