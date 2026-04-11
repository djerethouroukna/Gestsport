# reservations/management/commands/check_expired_reservations.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from notifications.utils import NotificationService
import logging

from reservations.models import Reservation, ReservationStatus

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Vérifie et met à jour les réservations expirées'

    def handle(self, *args, **options):
        """Commande principale"""
        self.stdout.write('🔍 Vérification des réservations expirées...')
        
        # Trouver les réservations confirmées qui sont expirées
        expired_reservations = Reservation.objects.filter(
            end_time__lt=timezone.now(),
            status=ReservationStatus.CONFIRMED
        )
        
        count = expired_reservations.count()
        
        if count == 0:
            self.stdout.write('✅ Aucune réservation expirée trouvée')
            return
        
        self.stdout.write(f'📋 {count} réservation(s) expirée(s) trouvée(s)')
        
        # Mettre à jour les statuts
        updated_count = expired_reservations.update(status=ReservationStatus.COMPLETED)
        
        # Notifier l'admin
        try:
            admin_users = User.objects.filter(is_superuser=True)
            
            for reservation in expired_reservations:
                message = (
                    f"🕐 Réservation expirée automatiquement\n\n"
                    f"📅 Date: {reservation.start_time.strftime('%d/%m/%Y')}\n"
                    f"⏰ Heure: {reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')}\n"
                    f"🏟️ Terrain: {reservation.terrain.name}\n"
                    f"👤 Utilisateur: {reservation.user.get_full_name() or reservation.user.email}\n"
                    f"🎫 Ticket: {reservation.ticket_set.first().ticket_number if reservation.ticket_set.exists() else 'N/A'}"
                )
                
                for admin in admin_users:
                    NotificationService.send_notification(
                        user=admin,
                        title="Réservation Expirée",
                        message=message,
                        notification_type="reservation_expired"
                    )
            
            self.stdout.write(f'📧 Notifications envoyées à {admin_users.count()} admin(s)')
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des notifications: {e}")
            self.stdout.write(f'❌ Erreur notifications: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ {updated_count} réservation(s) mise(s) à jour avec succès'
            )
        )
