# subscriptions/services.py
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from typing import List, Dict, Optional, Tuple

from .models import (
    Membership, Subscription, CreditPackage, UserCredit, RecurringReservation,
    MembershipType, SubscriptionStatus, RecurrenceType
)
from reservations.models import Reservation
from payments.models import Payment

User = get_user_model()


class SubscriptionService:
    """Service de gestion des abonnements"""
    
    @staticmethod
    def subscribe_user(
        user: User,
        membership: Membership,
        start_date: Optional[datetime] = None,
        auto_renew: bool = True
    ) -> Tuple[bool, str, Optional[Subscription]]:
        """Abonne un utilisateur à un type d'abonnement"""
        
        # Vérifier si l'utilisateur peut s'abonner
        can_subscribe, message = membership.can_user_subscribe(user)
        if not can_subscribe:
            return False, message, None
        
        # Vérifier si l'utilisateur a déjà un abonnement actif
        existing_subscription = Subscription.objects.filter(
            user=user,
            membership=membership,
            status=SubscriptionStatus.ACTIVE
        ).first()
        
        if existing_subscription:
            return False, "Vous avez déjà un abonnement actif à ce type", None
        
        # Calculer la date de début et de fin
        if start_date is None:
            start_date = timezone.now()
        
        end_date = start_date + timedelta(days=membership.duration_days)
        
        # Créer l'abonnement
        subscription = Subscription.objects.create(
            user=user,
            membership=membership,
            start_date=start_date,
            end_date=end_date,
            price_paid=membership.base_price,
            auto_renew=auto_renew,
            status=SubscriptionStatus.ACTIVE if not membership.requires_approval else SubscriptionStatus.INACTIVE
        )
        
        # Si validation requise, mettre en attente
        if membership.requires_approval:
            return True, "Abonnement créé en attente de validation", subscription
        
        return True, "Abonnement créé avec succès", subscription
    
    @staticmethod
    def approve_subscription(
        subscription_id: str,
        approved_by: User,
        approval_notes: str = ""
    ) -> Tuple[bool, str]:
        """Approuve un abonnement en attente"""
        try:
            subscription = Subscription.objects.get(id=subscription_id)
            
            if subscription.status != SubscriptionStatus.INACTIVE:
                return False, "Cet abonnement n'est pas en attente de validation"
            
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.approved_by = approved_by
            subscription.approval_notes = approval_notes
            subscription.save()
            
            return True, "Abonnement approuvé avec succès"
            
        except Subscription.DoesNotExist:
            return False, "Abonnement introuvable"
    
    @staticmethod
    def cancel_subscription(
        subscription_id: str,
        user: User,
        reason: str = ""
    ) -> Tuple[bool, str]:
        """Annule un abonnement"""
        try:
            subscription = Subscription.objects.get(id=subscription_id)
            
            # Vérifier les permissions
            if subscription.user != user and user.role not in ['admin', 'coach']:
                return False, "Permission refusée"
            
            if subscription.status != SubscriptionStatus.ACTIVE:
                return False, "Cet abonnement n'est pas actif"
            
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.save()
            
            return True, "Abonnement annulé avec succès"
            
        except Subscription.DoesNotExist:
            return False, "Abonnement introuvable"
    
    @staticmethod
    def renew_subscription(subscription_id: str) -> Tuple[bool, str]:
        """Renouvelle un abonnement"""
        try:
            subscription = Subscription.objects.get(id=subscription_id)
            
            if not subscription.auto_renew:
                return False, "Le renouvellement automatique n'est pas activé"
            
            if subscription.status != SubscriptionStatus.ACTIVE:
                return False, "L'abonnement n'est pas actif"
            
            # Calculer la nouvelle période
            new_end_date = subscription.end_date + timedelta(days=subscription.membership.duration_days)
            
            # Créer un nouvel abonnement
            new_subscription = Subscription.objects.create(
                user=subscription.user,
                membership=subscription.membership,
                start_date=subscription.end_date,
                end_date=new_end_date,
                price_paid=subscription.membership.base_price,
                auto_renew=subscription.auto_renew,
                status=SubscriptionStatus.ACTIVE
            )
            
            return True, "Abonnement renouvelé avec succès"
            
        except Subscription.DoesNotExist:
            return False, "Abonnement introuvable"
    
    @staticmethod
    def get_user_subscriptions(user: User) -> List[Subscription]:
        """Récupère les abonnements d'un utilisateur"""
        return Subscription.objects.filter(user=user).order_by('-created_at')
    
    @staticmethod
    def get_active_subscription(user: User) -> Optional[Subscription]:
        """Récupère l'abonnement actif d'un utilisateur"""
        return Subscription.objects.filter(
            user=user,
            status=SubscriptionStatus.ACTIVE,
            end_date__gt=timezone.now()
        ).first()
    
    @staticmethod
    def can_user_make_reservation(user: User, terrain=None) -> Tuple[bool, str, Optional[Subscription]]:
        """Vérifie si un utilisateur peut faire une réservation avec son abonnement"""
        active_subscription = SubscriptionService.get_active_subscription(user)
        
        if not active_subscription:
            return False, "Aucun abonnement actif", None
        
        # Vérifier si le terrain est autorisé
        if terrain and active_subscription.membership.allowed_terrains.exists():
            if terrain not in active_subscription.membership.allowed_terrains.all():
                return False, "Terrain non inclus dans l'abonnement", active_subscription
        
        # Vérifier les limites
        can_make, message = active_subscription.can_make_reservation
        return can_make, message, active_subscription
    
    @staticmethod
    def use_reservation_for_subscription(
        user: User,
        reservation: Reservation
    ) -> Tuple[bool, str]:
        """Utilise une réservation pour un abonnement"""
        can_make, message, subscription = SubscriptionService.can_user_make_reservation(
            user, reservation.terrain
        )
        
        if not can_make:
            return False, message
        
        # Calculer la durée
        duration_hours = Decimal(str(
            (reservation.end_time - reservation.start_time).total_seconds() / 3600
        ))
        
        # Enregistrer l'utilisation
        subscription.record_reservation_usage(duration_hours)
        
        return True, "Réservation utilisée avec l'abonnement"


class CreditService:
    """Service de gestion des crédits"""
    
    @staticmethod
    def purchase_credit_package(
        user: User,
        credit_package: CreditPackage,
        payment: Payment
    ) -> Tuple[bool, str, Optional[UserCredit]]:
        """Achète un forfait de crédits"""
        
        if not credit_package.is_active:
            return False, "Ce forfait n'est pas actif", None
        
        # Calculer la date d'expiration
        expires_at = None
        if credit_package.validity_days:
            expires_at = timezone.now() + timedelta(days=credit_package.validity_days)
        
        # Créer les crédits utilisateur
        user_credit = UserCredit.objects.create(
            user=user,
            credit_package=credit_package,
            amount=Decimal(str(credit_package.total_credits)),
            credit_type=credit_package.credit_type,
            expires_at=expires_at,
            transaction_id=payment.transaction.transaction_id if payment.transaction else None
        )
        
        return True, "Crédits achetés avec succès", user_credit
    
    @staticmethod
    def get_user_credits(user: User, credit_type: str = None) -> List[UserCredit]:
        """Récupère les crédits d'un utilisateur"""
        queryset = UserCredit.objects.filter(user=user)
        
        if credit_type:
            queryset = queryset.filter(credit_type=credit_type)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_available_credits(user: User, credit_type: str = None) -> Decimal:
        """Calcule le total des crédits disponibles"""
        credits = CreditService.get_user_credits(user, credit_type)
        
        total = Decimal('0')
        for credit in credits:
            if credit.is_available:
                total += credit.amount
        
        return total
    
    @staticmethod
    def use_credits(
        user: User,
        amount_to_use: Decimal,
        credit_type: str = 'hours'
    ) -> Tuple[bool, str, Decimal]:
        """Utilise des crédits"""
        available_credits = CreditService.get_user_credits(user, credit_type)
        
        total_available = Decimal('0')
        for credit in available_credits:
            if credit.is_available:
                total_available += credit.amount
        
        if total_available < amount_to_use:
            return False, f"Crédits insuffisants. Disponible: {total_available}, Requis: {amount_to_use}", Decimal('0')
        
        # Utiliser les crédits les plus anciens en premier (FIFO)
        remaining_amount = amount_to_use
        
        for credit in available_credits:
            if not credit.is_available or remaining_amount <= 0:
                continue
            
            if credit.amount >= remaining_amount:
                credit.use_credits(remaining_amount)
                remaining_amount = Decimal('0')
            else:
                remaining_amount -= credit.amount
                credit.use_credits(credit.amount)
        
        return True, "Crédits utilisés avec succès", amount_to_use
    
    @staticmethod
    def add_bonus_credits(
        user: User,
        amount: Decimal,
        credit_type: str = 'hours',
        reason: str = "",
        expires_at: Optional[datetime] = None
    ) -> UserCredit:
        """Ajoute des crédits bonus"""
        return UserCredit.objects.create(
            user=user,
            amount=amount,
            credit_type=credit_type,
            expires_at=expires_at,
            transaction_id=f"BONUS-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        )


class RecurringReservationService:
    """Service de gestion des réservations récurrentes"""
    
    @staticmethod
    def create_recurring_reservation(
        user: User,
        terrain,
        start_time: time,
        end_time: time,
        start_date: date,
        end_date: date,
        recurrence_pattern: Dict
    ) -> RecurringReservation:
        """Crée une réservation récurrente"""
        duration_minutes = int((
            datetime.combine(start_date, end_time) - 
            datetime.combine(start_date, start_time)
        ).total_seconds() / 60)
        
        return RecurringReservation.objects.create(
            user=user,
            terrain=terrain,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            start_date=start_date,
            end_date=end_date,
            recurrence_pattern=recurrence_pattern
        )
    
    @staticmethod
    def generate_reservations_for_period(
        recurring_reservation: RecurringReservation,
        days_ahead: int = 30
    ) -> List[Reservation]:
        """Génère les réservations pour une période"""
        # TODO: Implémenter la génération basée sur le pattern
        # Pour l'instant, retourner une liste vide
        return []
    
    @staticmethod
    def get_user_recurring_reservations(user: User) -> List[RecurringReservation]:
        """Récupère les réservations récurrentes d'un utilisateur"""
        return RecurringReservation.objects.filter(
            user=user,
            is_active=True
        ).order_by('-created_at')


class MembershipService:
    """Service de gestion des types d'abonnements"""
    
    @staticmethod
    def create_membership(
        name: str,
        description: str,
        membership_type: str,
        base_price: Decimal,
        duration_days: int,
        recurrence_type: str,
        **kwargs
    ) -> Membership:
        """Crée un type d'abonnement"""
        return Membership.objects.create(
            name=name,
            description=description,
            membership_type=membership_type,
            base_price=base_price,
            duration_days=duration_days,
            recurrence_type=recurrence_type,
            **kwargs
        )
    
    @staticmethod
    def get_popular_memberships(limit: int = 5) -> List[Membership]:
        """Récupère les abonnements populaires"""
        return Membership.objects.filter(
            is_active=True,
            is_public=True
        ).order_by('-base_price')[:limit]
    
    @staticmethod
    def get_memberships_for_user(user: User) -> List[Membership]:
        """Récupère les abonnements disponibles pour un utilisateur"""
        return Membership.objects.filter(
            is_active=True,
            is_public=True
        )
    
    @staticmethod
    def create_individual_membership(
        name: str,
        base_price: Decimal,
        max_reservations_per_month: int = None
    ) -> Membership:
        """Crée un abonnement individuel standard"""
        return MembershipService.create_membership(
            name=name,
            description=f"Abonnement individuel avec {max_reservations_per_month or 'illimité'} réservations par mois",
            membership_type=MembershipType.INDIVIDUAL,
            base_price=base_price,
            duration_days=30,
            recurrence_type=RecurrenceType.MONTHLY,
            max_reservations_per_month=max_reservations_per_month
        )
    
    @staticmethod
    def create_family_membership(
        name: str,
        base_price: Decimal,
        max_members: int = 4
    ) -> Membership:
        """Crée un abonnement familial"""
        return MembershipService.create_membership(
            name=name,
            description=f"Abonnement familial pour {max_members} membres",
            membership_type=MembershipType.FAMILY,
            base_price=base_price,
            duration_days=30,
            recurrence_type=RecurrenceType.MONTHLY,
            max_reservations_per_month=max_members * 4  # 4 réservations par membre par mois
        )
    
    @staticmethod
    def create_student_membership(
        name: str,
        base_price: Decimal,
        discount_percentage: Decimal = Decimal('20')
    ) -> Membership:
        """Crée un abonnement étudiant"""
        return MembershipService.create_membership(
            name=name,
            description="Abonnement étudiant avec réduction spéciale",
            membership_type=MembershipType.STUDENT,
            base_price=base_price,
            duration_days=30,
            recurrence_type=RecurrenceType.MONTHLY,
            discount_percentage=discount_percentage,
            requires_approval=True  # Nécessite validation du statut étudiant
        )
