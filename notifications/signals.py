from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .utils import NotificationService
from reservations.models import Reservation, ReservationStatus
from activities.models import Activity, ActivityStatus

@receiver(post_save, sender=Reservation)
def reservation_created_notification(sender, instance, created, **kwargs):
    """Envoyer une notification quand une réservation est créée"""
    if created and instance.status == ReservationStatus.PENDING:
        NotificationService.notify_reservation_pending(instance)

@receiver(pre_save, sender=Reservation)
def reservation_status_change_notification(sender, instance, **kwargs):
    """Envoyer une notification quand le statut de réservation change"""
    if not instance.pk:  # Nouvelle réservation
        return
    
    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            if instance.status == 'confirmed':
                NotificationService.notify_reservation_confirmed(instance)
            elif instance.status == 'cancelled':
                NotificationService.notify_reservation_cancelled(instance)
            elif instance.status == 'rejected':
                NotificationService.notify_reservation_rejected(instance)
    except sender.DoesNotExist:
        pass

@receiver(post_save, sender=Activity)
def activity_created_notification(sender, instance, created, **kwargs):
    """Envoyer une notification quand une activité est créée"""
    if created and instance.status == ActivityStatus.CONFIRMED:
        # Notifier les participants déjà inscrits
        for participant in instance.participants.all():
            NotificationService.create_notification(
                recipient=participant,
                title=f"Nouvelle activité : {instance.title}",
                message=f"Une nouvelle activité '{instance.title}' a été créée pour le {instance.start_time.strftime('%d/%m/%Y à %H:%M')} sur le terrain {instance.terrain.name}.",
                notification_type='activity_reminder',
                content_object=instance
            )

@receiver(pre_save, sender=Activity)
def activity_status_change_notification(sender, instance, **kwargs):
    """Envoyer une notification quand le statut d'une activité change"""
    if not instance.pk:
        return
    
    try:
        old_instance = Activity.objects.get(pk=instance.pk)
        
        # Vérifier si l'activité est annulée
        if old_instance.status != ActivityStatus.CANCELLED and instance.status == ActivityStatus.CANCELLED:
            NotificationService.notify_activity_cancelled(instance)
        
        # Vérifier si la date/heure a changé
        if old_instance.start_time != instance.start_time:
            NotificationService.notify_activity_modified(instance, old_instance.start_time)
    except Activity.DoesNotExist:
        pass
