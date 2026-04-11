# waitinglist/services.py
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from typing import List, Dict, Optional, Tuple

from .models import (
    WaitingList, WaitingListConfiguration, WaitingListNotification,
    WaitingListStatistics, WaitingListStatus, WaitingListPriority
)
from timeslots.models import TimeSlot
from reservations.models import Reservation
from notifications.utils import NotificationService

User = get_user_model()


class WaitingListService:
    """Service de gestion de la liste d'attente"""
    
    @staticmethod
    def add_to_waiting_list(
        user: User,
        terrain,
        target_date: date,
        start_time: time,
        end_time: time,
        priority: str = WaitingListPriority.NORMAL,
        flexible_times: bool = True,
        flexible_date: bool = False,
        notes: str = ""
    ) -> Tuple[bool, str, Optional[WaitingList]]:
        """Ajoute un utilisateur à la liste d'attente"""
        
        # Vérifier si la liste d'attente est activée pour ce terrain
        config = WaitingListService.get_terrain_config(terrain)
        if not config or not config.is_enabled:
            return False, "La liste d'attente n'est pas activée pour ce terrain", None
        
        # Vérifier si l'utilisateur est déjà dans la liste d'attente pour cette période
        existing_entry = WaitingList.objects.filter(
            user=user,
            terrain=terrain,
            date=target_date,
            start_time=start_time,
            end_time=end_time,
            status=WaitingListStatus.WAITING
        ).first()
        
        if existing_entry:
            return False, "Vous êtes déjà dans la liste d'attente pour cette période", existing_entry
        
        # Vérifier le nombre maximum d'entrées par jour
        daily_count = WaitingList.objects.filter(
            terrain=terrain,
            date=target_date,
            status=WaitingListStatus.WAITING
        ).count()
        
        if daily_count >= config.max_entries_per_day:
            return False, "La liste d'attente est complète pour cette date", None
        
        # Calculer la durée
        duration_minutes = int((
            datetime.combine(target_date, end_time) - 
            datetime.combine(target_date, start_time)
        ).total_seconds() / 60)
        
        # Calculer le score de priorité si activé
        if config.enable_priority_scoring:
            priority = WaitingListService.calculate_priority_score(user, priority)
        
        # Créer l'entrée
        waiting_list_entry = WaitingList.objects.create(
            user=user,
            terrain=terrain,
            date=target_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            priority=priority,
            flexible_times=flexible_times,
            flexible_date=flexible_date,
            notes=notes
        )
        
        return True, "Ajouté à la liste d'attente avec succès", waiting_list_entry
    
    @staticmethod
    def calculate_priority_score(user: User, base_priority: str) -> str:
        """Calcule le score de priorité d'un utilisateur"""
        config = WaitingListService.get_terrain_config(None)  # Config générale
        
        score = 0
        
        # Score de base
        priority_scores = {
            WaitingListPriority.LOW: 0,
            WaitingListPriority.NORMAL: 50,
            WaitingListPriority.HIGH: 75,
            WaitingListPriority.URGENT: 100
        }
        score += priority_scores.get(base_priority, 50)
        
        if config:
            # Bonus VIP
            if hasattr(user, 'is_vip') and user.is_vip:
                score += config.vip_score_bonus
            
            # Bonus utilisateur fréquent
            recent_reservations = Reservation.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            if recent_reservations >= 5:
                score += config.frequent_user_score_bonus
            elif recent_reservations >= 10:
                score += config.frequent_user_score_bonus * 2
            
            # Bonus longue attente (sera calculé lors du traitement)
        
        # Convertir le score en priorité
        if score >= 90:
            return WaitingListPriority.URGENT
        elif score >= 70:
            return WaitingListPriority.HIGH
        elif score >= 30:
            return WaitingListPriority.NORMAL
        else:
            return WaitingListPriority.LOW
    
    @staticmethod
    def process_available_timeslot(timeslot: TimeSlot) -> List[WaitingList]:
        """Traite un créneau disponible et notifie les utilisateurs concernés"""
        
        # Récupérer les entrées correspondantes
        matching_entries = []
        all_entries = WaitingList.objects.filter(
            terrain=timeslot.terrain,
            date=timeslot.date,
            status=WaitingListStatus.WAITING
        ).order_by('-priority', 'created_at')
        
        # Filtrer selon les préférences
        for entry in all_entries:
            if entry.can_match_timeslot(timeslot):
                # Vérifier le nombre maximum de notifications
                config = WaitingListService.get_terrain_config(timeslot.terrain)
                if config and entry.notification_count >= config.max_notifications_per_user:
                    continue
                
                matching_entries.append(entry)
                
                # Notifier l'utilisateur
                WaitingListService.notify_user(entry, timeslot)
        
        return matching_entries
    
    @staticmethod
    def notify_user(waiting_list_entry: WaitingList, timeslot: TimeSlot) -> WaitingListNotification:
        """Notifie un utilisateur qu'un créneau est disponible"""
        
        # Créer la notification
        notification = WaitingListNotification.objects.create(
            waiting_list_entry=waiting_list_entry,
            notification_type='timeslot_available',
            proposed_timeslot_id=timeslot.id,
            proposed_date=timeslot.date,
            proposed_start_time=timeslot.start_time,
            proposed_end_time=timeslot.end_time,
            message=f"Un créneau est disponible pour {timeslot.terrain.name} le {timeslot.date} de {timeslot.start_time} à {timeslot.end_time}"
        )
        
        # Mettre à jour le statut de l'entrée
        waiting_list_entry.notify_user(timeslot)
        
        # Envoyer la notification (via le service de notifications)
        try:
            NotificationService.create_notification(
                recipient=waiting_list_entry.user,
                title="Créneau disponible",
                message=notification.message,
                notification_type='waiting_list_available',
                content_object=waiting_list_entry
            )
        except Exception as e:
            print(f"Erreur notification: {e}")
        
        return notification
    
    @staticmethod
    def accept_notification(notification_id: str, user: User) -> Tuple[bool, str, Optional[Reservation]]:
        """Accepte une notification de liste d'attente"""
        try:
            notification = WaitingListNotification.objects.get(
                id=notification_id,
                waiting_list_entry__user=user
            )
            
            if notification.response:
                return False, "Cette notification a déjà reçu une réponse", None
            
            if notification.waiting_list_entry.notification_expired:
                return False, "Cette notification a expiré", None
            
            # Créer la réservation
            waiting_list_entry = notification.waiting_list_entry
            
            start_datetime = datetime.combine(
                notification.proposed_date,
                notification.proposed_start_time
            )
            end_datetime = datetime.combine(
                notification.proposed_date,
                notification.proposed_end_time
            )
            
            reservation = Reservation.objects.create(
                user=user,
                terrain=waiting_list_entry.terrain,
                start_time=start_datetime,
                end_time=end_datetime,
                status='pending',
                notes=f"Réservation depuis liste d'attente: {waiting_list_entry.notes}"
            )
            
            # Mettre à jour les statuts
            waiting_list_entry.accept_offer(reservation)
            notification.response = 'accepted'
            notification.responded_at = timezone.now()
            notification.save()
            
            # Réserver le créneau
            from timeslots.services import TimeSlotService
            TimeSlotService.book_timeslot(notification.proposed_timeslot_id, reservation)
            
            return True, "Réservation créée avec succès", reservation
            
        except WaitingListNotification.DoesNotExist:
            return False, "Notification introuvable", None
    
    @staticmethod
    def decline_notification(notification_id: str, user: User) -> Tuple[bool, str]:
        """Décline une notification de liste d'attente"""
        try:
            notification = WaitingListNotification.objects.get(
                id=notification_id,
                waiting_list_entry__user=user
            )
            
            if notification.response:
                return False, "Cette notification a déjà reçu une réponse", None
            
            waiting_list_entry = notification.waiting_list_entry
            
            # Mettre à jour les statuts
            waiting_list_entry.decline_offer()
            notification.response = 'declined'
            notification.responded_at = timezone.now()
            notification.save()
            
            return True, "Offre déclinée"
            
        except WaitingListNotification.DoesNotExist:
            return False, "Notification introuvable"
    
    @staticmethod
    def cancel_waiting_list_entry(entry_id: str, user: User) -> Tuple[bool, str]:
        """Annule une entrée dans la liste d'attente"""
        try:
            entry = WaitingList.objects.get(id=entry_id, user=user)
            
            if not entry.is_active:
                return False, "Cette entrée n'est plus active"
            
            entry.cancel()
            return True, "Entrée annulée avec succès"
            
        except WaitingList.DoesNotExist:
            return False, "Entrée introuvable"
    
    @staticmethod
    def get_user_waiting_list(user: User, terrain=None) -> List[WaitingList]:
        """Récupère la liste d'attente d'un utilisateur"""
        queryset = WaitingList.objects.filter(user=user)
        
        if terrain:
            queryset = queryset.filter(terrain=terrain)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_terrain_waiting_list(terrain, target_date: date = None) -> List[WaitingList]:
        """Récupère la liste d'attente pour un terrain"""
        queryset = WaitingList.objects.filter(terrain=terrain, status=WaitingListStatus.WAITING)
        
        if target_date:
            queryset = queryset.filter(date=target_date)
        
        return queryset.order_by('-priority', 'created_at')
    
    @staticmethod
    def get_terrain_config(terrain) -> Optional[WaitingListConfiguration]:
        """Récupère la configuration de la liste d'attente pour un terrain"""
        try:
            return WaitingListConfiguration.objects.get(terrain=terrain)
        except WaitingListConfiguration.DoesNotExist:
            return None
    
    @staticmethod
    def cleanup_expired_notifications():
        """Nettoie les notifications expirées"""
        expired_entries = WaitingList.objects.filter(
            status=WaitingListStatus.NOTIFIED,
            notification_expires_at__lt=timezone.now()
        )
        
        count = 0
        for entry in expired_entries:
            entry.status = WaitingListStatus.EXPIRED
            entry.save()
            count += 1
        
        return count
    
    @staticmethod
    def update_daily_statistics(target_date: date = None):
        """Met à jour les statistiques quotidiennes"""
        if target_date is None:
            target_date = timezone.now().date()
        
        for terrain in WaitingList.objects.values_list('terrain', flat=True).distinct():
            from terrains.models import Terrain
            
            try:
                terrain_obj = Terrain.objects.get(id=terrain)
                stats = WaitingListService.calculate_daily_stats(terrain_obj, target_date)
                
                WaitingListStatistics.objects.update_or_create(
                    terrain=terrain_obj,
                    date=target_date,
                    defaults=stats
                )
            except Terrain.DoesNotExist:
                continue
    
    @staticmethod
    def calculate_daily_stats(terrain, target_date: date) -> Dict:
        """Calcule les statistiques quotidiennes"""
        entries = WaitingList.objects.filter(
            terrain=terrain,
            date=target_date
        )
        
        # Statistiques de base
        total_entries = entries.count()
        new_entries = entries.filter(created_at__date=target_date).count()
        resolved_entries = entries.filter(
            status__in=[WaitingListStatus.ACCEPTED, WaitingListStatus.CANCELLED]
        ).count()
        
        # Répartitions
        entries_by_priority = {}
        for priority in WaitingListPriority.choices:
            entries_by_priority[priority[0]] = entries.filter(priority=priority[0]).count()
        
        entries_by_status = {}
        for status in WaitingListStatus.choices:
            entries_by_status[status[0]] = entries.filter(status=status[0]).count()
        
        # Notifications
        notifications = WaitingListNotification.objects.filter(
            waiting_list_entry__terrain=terrain,
            sent_at__date=target_date
        )
        
        notifications_sent = notifications.count()
        notifications_accepted = notifications.filter(response='accepted').count()
        notifications_declined = notifications.filter(response='declined').count()
        
        # Temps d'attente moyen
        resolved = entries.filter(status=WaitingListStatus.ACCEPTED)
        avg_waiting_time = 0
        
        if resolved.exists():
            total_time = sum(
                (entry.updated_at - entry.created_at).total_seconds() / 3600
                for entry in resolved
            )
            avg_waiting_time = total_time / resolved.count()
        
        # Taux de conversion
        conversion_rate = 0
        if total_entries > 0:
            conversion_rate = (resolved_entries / total_entries) * 100
        
        return {
            'total_entries': total_entries,
            'new_entries': new_entries,
            'resolved_entries': resolved_entries,
            'entries_by_priority': entries_by_priority,
            'entries_by_status': entries_by_status,
            'notifications_sent': notifications_sent,
            'notifications_accepted': notifications_accepted,
            'notifications_declined': notifications_declined,
            'avg_waiting_time_hours': avg_waiting_time,
            'conversion_rate': conversion_rate
        }


class WaitingListAutoProcessor:
    """Service de traitement automatique de la liste d'attente"""
    
    @staticmethod
    def process_cancellations():
        """Traite les annulations de réservations et notifie la liste d'attente"""
        from reservations.models import Reservation
        
        # Récupérer les réservations annulées récemment
        cancelled_reservations = Reservation.objects.filter(
            status='cancelled',
            updated_at__gte=timezone.now() - timedelta(hours=1)
        )
        
        for reservation in cancelled_reservations:
            # Récupérer le créneau associé
            if hasattr(reservation, 'timeslot'):
                timeslot = reservation.timeslot
                
                # Libérer le créneau
                timeslot.mark_as_available()
                
                # Traiter la liste d'attente
                WaitingListService.process_available_timeslot(timeslot)
    
    @staticmethod
    def process_expired_notifications():
        """Traite les notifications expirées"""
        return WaitingListService.cleanup_expired_notifications()
    
    @staticmethod
    def send_reminder_notifications():
        """Envoie des rappels pour les notifications bientôt expirées"""
        soon_to_expire = WaitingList.objects.filter(
            status=WaitingListStatus.NOTIFIED,
            notification_expires_at__lte=timezone.now() + timedelta(hours=2),
            notification_expires_at__gt=timezone.now()
        )
        
        for entry in soon_to_expire:
            try:
                NotificationService.create_notification(
                    recipient=entry.user,
                    title="Rappel: Offre de réservation expire bientôt",
                    message=f"Votre offre pour {entry.terrain.name} expire dans moins de 2 heures. Répondez rapidement pour ne pas la manquer.",
                    notification_type='waiting_list_reminder',
                    content_object=entry
                )
            except Exception as e:
                print(f"Erreur rappel: {e}")
