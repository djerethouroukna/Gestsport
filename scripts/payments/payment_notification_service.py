# payment_notification_service.py
from django.db import connection
from django.utils import timezone
from users.models import User

class PaymentNotificationService:
    """Service pour gérer les notifications de paiement aux admins"""
    
    @staticmethod
    def create_payment_notification(reservation, payment):
        """Crée une notification pour tous les admins quand un paiement est réussi"""
        try:
            admins = User.objects.filter(role='admin')
            
            for admin in admins:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO admin_notifications 
                        (reservation_id, payment_id, admin_email, message, is_read, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, [
                        reservation.id,
                        payment.id if payment else None,
                        admin.email,
                        f"🔔 PAIEMENT REÇU - Réservation {reservation.id} par {reservation.user.email} - Montant: {payment.amount if payment else 'N/A'} {payment.currency if payment else 'XOF'}",
                        False,
                        timezone.now()
                    ])
            
            print(f"✅ Notifications créées pour {admins.count()} admin(s)")
            return True
            
        except Exception as e:
            print(f"❌ Erreur création notification: {e}")
            return False
    
    @staticmethod
    def create_confirmation_notification(reservation, confirmed_by):
        """Crée une notification quand une réservation est confirmée"""
        try:
            # Notifier le coach que sa réservation est confirmée
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO admin_notifications 
                    (reservation_id, admin_email, message, is_read, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, [
                    reservation.id,
                    reservation.user.email,
                    f"✅ RÉSERVATION CONFIRMÉE - Votre réservation {reservation.id} a été confirmée par {confirmed_by.get_full_name() or confirmed_by.email}",
                    False,
                    timezone.now()
                ])
            
            print(f"✅ Notification de confirmation créée pour {reservation.user.email}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur notification confirmation: {e}")
            return False
    
    @staticmethod
    def get_unread_count(admin_email):
        """Retourne le nombre de notifications non lues pour un admin"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM admin_notifications 
                    WHERE admin_email = %s AND is_read = FALSE
                """, [admin_email])
                count = cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"❌ Erreur comptage notifications: {e}")
            return 0
