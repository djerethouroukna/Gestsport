from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Notification, NotificationType, NotificationPriority
from django.contrib.contenttypes.models import ContentType
from .email_service import EmailService

User = get_user_model()

class NotificationService:
    """Service pour gérer les notifications"""
    
    @staticmethod
    def get_notification_recipients(action_type, reservation=None, activity=None, chat_message=None):
        """Déterminer qui doit recevoir les notifications selon l'action et le rôle"""
        recipients = []
        
        if action_type == 'reservation_pending':
            # Réservation en attente → admins et UNIQUEMENT le coach concerné si c'est sa réservation
            admins = User.objects.filter(role='admin', is_active=True)
            recipients.extend(list(admins))
            
            # Si la réservation est faite par un coach, uniquement ce coach la voit
            if reservation and reservation.user and reservation.user.role == 'coach':
                recipients.append(reservation.user)
            # Si la réservation est faite par un joueur, tous les coaches la voient
            elif reservation and reservation.user and reservation.user.role == 'player':
                coaches = User.objects.filter(role='coach', is_active=True)
                recipients.extend(list(coaches))
            
        elif action_type == 'reservation_confirmed':
            # Réservation confirmée → l'utilisateur qui a réservé + TOUS les admins
            if reservation and reservation.user:
                recipients.append(reservation.user)  # TOUS les utilisateurs voient leurs confirmations
            admins = User.objects.filter(role='admin', is_active=True)
            recipients.extend(list(admins))
            
        elif action_type == 'reservation_rejected':
            # Réservation rejetée → l'utilisateur qui a réservé + TOUS les admins
            if reservation and reservation.user:
                recipients.append(reservation.user)  # TOUS les utilisateurs voient leurs rejets
            admins = User.objects.filter(role='admin', is_active=True)
            recipients.extend(list(admins))
            
        elif action_type == 'reservation_cancelled':
            # Réservation annulée → l'utilisateur + TOUS les admins + autres coaches
            if reservation and reservation.user:
                recipients.append(reservation.user)  # TOUS les utilisateurs voient leurs annulations
            admins = User.objects.filter(role='admin', is_active=True)
            recipients.extend(list(admins))
            # Les autres coaches voient aussi l'annulation (sauf si c'est le même utilisateur)
            coaches = User.objects.filter(role='coach', is_active=True).exclude(id=reservation.user.id if reservation.user else None)
            recipients.extend(list(coaches))
            
        elif action_type == 'activity_reminder':
            # Rappel activité → UNIQUEMENT les participants + le coach de l'activité
            if activity:
                # Tous les participants concernés (peu importe leur rôle)
                participants = activity.participants.filter(is_active=True)
                recipients.extend(list(participants))
                
                # Le coach de l'activité reçoit aussi le rappel
                if activity.coach:
                    recipients.append(activity.coach)
                    
        elif action_type == 'activity_cancelled':
            # Activité annulée → participants + coach de l'activité + admins
            if activity:
                # Tous les participants de l'activité
                participants = activity.participants.filter(is_active=True)
                recipients.extend(list(participants))
                
                # Le coach de l'activité
                if activity.coach:
                    recipients.append(activity.coach)
                    
                # Tous les admins sont notifiés
                admins = User.objects.filter(role='admin', is_active=True)
                recipients.extend(list(admins))
                
        elif action_type == 'activity_modified':
            # Activité modifiée → participants + coach de l'activité
            if activity:
                # Tous les participants de l'activité
                participants = activity.participants.filter(is_active=True)
                recipients.extend(list(participants))
                
                # Le coach de l'activité
                if activity.coach:
                    recipients.append(activity.coach)
        
        elif action_type == 'chat_message':
            # Message de chat → uniquement les participants concernés
            if chat_message:
                # Tous les utilisateurs concernés par ce chat
                recipients.extend(list(chat_message.chat_room.participants.all()))
        
        # Éviter les doublons
        return list(set(recipients))
    
    @staticmethod
    def create_notification(recipient, title, message, notification_type, 
                          priority=NotificationPriority.MEDIUM, 
                          content_object=None):
        """Créer une notification"""
        notification = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority
        )
        
        # Lier à un objet si fourni
        if content_object:
            notification.content_type = ContentType.objects.get_for_model(content_object)
            notification.object_id = content_object.id
            notification.save()
        
        return notification
    
    @staticmethod
    def notify_chat_message(chat_message):
        """Notifier les participants d'un nouveau message de chat"""
        recipients = NotificationService.get_notification_recipients('chat_message', chat_message=chat_message)
        
        for recipient in recipients:
            # Ne pas notifier l'expéditeur du message
            if recipient == chat_message.sender:
                continue
                
            title = f"Nouveau message dans {chat_message.chat_room.name}"
            message = f"{chat_message.sender.get_full_name()}: {chat_message.content[:100]}..."
            
            NotificationService.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type='chat_message',
                priority=NotificationPriority.LOW,
                content_object=chat_message
            )
    
    @staticmethod
    def notify_reservation_pending(reservation):
        """Notifier les admins et coaches d'une nouvelle réservation en attente"""
        recipients = NotificationService.get_notification_recipients('reservation_pending', reservation=reservation)
        
        for recipient in recipients:
            title = "Nouvelle réservation en attente"
            if recipient.role == 'admin':
                message = f"L'entraîneur {reservation.user.get_full_name()} a réservé {reservation.terrain.name} le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')}. Validation requise."
            else:  # coach
                message = f"Nouvelle réservation de {reservation.user.get_full_name()} pour {reservation.terrain.name} le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')}."
            
            NotificationService.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=NotificationType.RESERVATION_PENDING,
                priority=NotificationPriority.HIGH,
                content_object=reservation
            )
    
    @staticmethod
    def notify_reservation_confirmed(reservation):
        """Notifier les personnes concernées que la réservation est confirmée"""
        recipients = NotificationService.get_notification_recipients('reservation_confirmed', reservation=reservation)
        
        # Envoyer un email professionnel
        EmailService.send_reservation_notification(reservation, 'confirmed')
        
        for recipient in recipients:
            if recipient == reservation.user:
                # Message pour l'utilisateur qui a réservé
                title = "Réservation confirmée"
                message = f"Votre réservation du terrain {reservation.terrain.name} pour le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été confirmée."
            else:  # admin
                # Message pour les admins
                title = "Réservation confirmée"
                message = f"La réservation de {reservation.user.get_full_name()} pour {reservation.terrain.name} le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été confirmée."
            
            NotificationService.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=NotificationType.RESERVATION_CONFIRMED,
                priority=NotificationPriority.HIGH,
                content_object=reservation
            )
    
    @staticmethod
    def notify_reservation_rejected(reservation):
        """Notifier les personnes concernées que la réservation est rejetée"""
        recipients = NotificationService.get_notification_recipients('reservation_rejected', reservation=reservation)
        
        for recipient in recipients:
            if recipient == reservation.user:
                # Message pour l'utilisateur qui a réservé
                title = "Réservation rejetée"
                message = f"Votre réservation du terrain {reservation.terrain.name} pour le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été rejetée."
            else:  # admin
                # Message pour les admins
                title = "Réservation rejetée"
                message = f"La réservation de {reservation.user.get_full_name()} pour {reservation.terrain.name} le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été rejetée."
            
            NotificationService.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=NotificationType.RESERVATION_REJECTED,
                priority=NotificationPriority.HIGH,
                content_object=reservation
            )
    
    @staticmethod
    def notify_reservation_cancelled(reservation):
        """Notifier les personnes concernées de l'annulation d'une réservation"""
        recipients = NotificationService.get_notification_recipients('reservation_cancelled', reservation=reservation)
        
        for recipient in recipients:
            if recipient == reservation.user:
                # Message pour l'utilisateur qui a annulé
                title = "Réservation annulée"
                message = f"Votre réservation du terrain {reservation.terrain.name} pour le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été annulée."
            elif recipient.role == 'admin':
                # Message pour les admins
                title = "Réservation annulée"
                message = f"La réservation de {reservation.user.get_full_name()} pour {reservation.terrain.name} le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été annulée."
            else:  # autre coach
                # Message pour les autres coaches
                title = "Réservation annulée"
                message = f"La réservation de {reservation.user.get_full_name()} pour {reservation.terrain.name} le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} a été annulée."
            
            NotificationService.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=NotificationType.RESERVATION_CANCELLED,
                priority=NotificationPriority.MEDIUM,
                content_object=reservation
            )
    
    @staticmethod
    def notify_activity_reminder(activity, hours_before=2):
        """Envoyer un rappel avant une activité"""
        participants = activity.participants.all()
        
        for participant in participants:
            NotificationService.create_notification(
                recipient=participant,
                title=f"Rappel : {activity.title}",
                message=f"Rappel : Votre activité '{activity.title}' commence dans {hours_before} heures à {activity.start_time.strftime('%H:%M')} sur le terrain {activity.terrain.name}.",
                notification_type=NotificationType.ACTIVITY_REMINDER,
                priority=NotificationPriority.MEDIUM,
                content_object=activity
            )
        
        # Notifier le coach aussi
        if activity.coach:
            NotificationService.create_notification(
                recipient=activity.coach,
                title=f"Rappel : {activity.title}",
                message=f"Rappel : Votre activité '{activity.title}' commence dans {hours_before} heures à {activity.start_time.strftime('%H:%M')} sur le terrain {activity.terrain.name}.",
                notification_type=NotificationType.ACTIVITY_REMINDER,
                priority=NotificationPriority.MEDIUM,
                content_object=activity
            )
    
    @staticmethod
    def notify_activity_cancelled(activity):
        """Notifier de l'annulation d'une activité"""
        participants = activity.participants.all()
        
        for participant in participants:
            NotificationService.create_notification(
                recipient=participant,
                title=f"Activité annulée : {activity.title}",
                message=f"L'activité '{activity.title}' prévue le {activity.start_time.strftime('%d/%m/%Y à %H:%M')} a été annulée.",
                notification_type=NotificationType.ACTIVITY_CANCELLED,
                priority=NotificationPriority.HIGH,
                content_object=activity
            )
    
    @staticmethod
    def notify_reservation_payment(reservation, amount, payment):
        """Notifier du paiement d'une réservation - réparti par coach"""
        recipients = []
        
        # L'utilisateur qui a payé reçoit une confirmation
        if reservation.user:
            recipients.append(reservation.user)
        
        # Le coach associé à la réservation reçoit une notification
        # (si c'est une réservation de coaching ou si le terrain a un coach assigné)
        if hasattr(reservation, 'coach') and reservation.coach:
            recipients.append(reservation.coach)
        elif hasattr(reservation.terrain, 'coach') and reservation.terrain.coach:
            recipients.append(reservation.terrain.coach)
        
        # Tous les admins reçoivent une notification
        admins = User.objects.filter(role='admin', is_active=True)
        recipients.extend(list(admins))
        
        for recipient in recipients:
            if recipient == reservation.user:
                # Message pour l'utilisateur qui a payé
                title = "Paiement effectué"
                message = f"Votre paiement de {amount} F CFA pour la réservation du terrain {reservation.terrain.name} a été reçu."
            elif recipient in [getattr(reservation, 'coach', None), getattr(reservation.terrain, 'coach', None)]:
                # Message pour le coach concerné
                title = "Paiement réservation reçu"
                message = f"Un paiement de {amount} F CFA a été effectué pour la réservation de {reservation.user.get_full_name()} sur le terrain {reservation.terrain.name}."
            else:  # admin
                # Message pour les admins
                title = "Paiement réservation effectué"
                message = f"Un paiement de {amount} F CFA a été effectué par {reservation.user.get_full_name()} pour la réservation #{reservation.id}."
            
            NotificationService.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=NotificationType.PAYMENT_VALIDATED,
                priority=NotificationPriority.HIGH,
                content_object=payment
            )
    
    @staticmethod
    def notify_coach_payment(coach, amount, payment):
        """Notifier l'admin et le coach d'un paiement d'entraîneur"""
        recipients = []
        
        # Le coach reçoit une notification
        recipients.append(coach)
        
        # Tous les admins reçoivent aussi une notification
        admins = User.objects.filter(role='admin', is_active=True)
        recipients.extend(list(admins))
        
        for recipient in recipients:
            if recipient == coach:
                # Message pour le coach
                title = "Paiement reçu"
                message = f"Vous avez reçu un paiement de {amount} F CFA pour vos services d'entraînement."
            else:  # admin
                # Message pour les admins
                title = "Paiement entraîneur effectué"
                message = f"L'entraîneur {coach.get_full_name()} a reçu un paiement de {amount} F CFA."
            
            NotificationService.create_notification(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=NotificationType.COACH_PAYMENT,
                priority=NotificationPriority.HIGH,
                content_object=payment
            )

class ReminderService:
    """Service pour gérer les rappels automatiques"""
    
    @staticmethod
    def schedule_activity_reminders():
        """Programmer les rappels pour les activités à venir"""
        from activities.models import Activity
        
        now = timezone.now()
        
        # Rappels 2 heures avant
        reminder_time_2h = now + timedelta(hours=2)
        activities_2h = Activity.objects.filter(
            start_time=reminder_time_2h,
            status='confirmed'
        )
        
        for activity in activities_2h:
            NotificationService.notify_activity_reminder(activity, hours_before=2)
        
        # Rappels 24 heures avant
        reminder_time_24h = now + timedelta(hours=24)
        activities_24h = Activity.objects.filter(
            start_time=reminder_time_24h,
            status='confirmed'
        )
        
        for activity in activities_24h:
            NotificationService.notify_activity_reminder(activity, hours_before=24)
    
    @staticmethod
    def schedule_reservation_reminders():
        """Programmer les rappels pour les réservations à venir"""
        from reservations.models import Reservation
        
        now = timezone.now()
        
        # Rappels 2 heures avant
        reminder_time_2h = now + timedelta(hours=2)
        reservations_2h = Reservation.objects.filter(
            start_time=reminder_time_2h,
            status='confirmed'
        )
        
        for reservation in reservations_2h:
            NotificationService.create_notification(
                recipient=reservation.user,
                title=f"Rappel réservation : {reservation.terrain.name}",
                message=f"Rappel : Votre réservation du terrain {reservation.terrain.name} commence dans 2 heures à {reservation.start_time.strftime('%H:%M')}.",
                notification_type=NotificationType.ACTIVITY_REMINDER,
                priority=NotificationPriority.MEDIUM,
                content_object=reservation
            )
