import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone

from reservations.models import Reservation
from payments.models import Payment

print("=== CORRECTION PAIEMENT RÉSERVATION 17 ===")

try:
    reservation = Reservation.objects.get(id=17)
    payment = Payment.objects.filter(reservation=reservation).first()
    
    print(f"Réservation 17: {reservation.status} - {reservation.is_paid}")
    print(f"Payment: {payment.status} - {payment.amount}")
    
    if payment:
        # Mettre à jour le statut du paiement manuellement
        payment.status = 'paid'
        payment.paid_at = timezone.now()
        # Ne pas mettre transaction_id pour éviter l'erreur UUID
        payment.save()
        
        print(f"✅ Payment status mis à jour à 'paid'")
        print(f"✅ Payment paid_at: {payment.paid_at}")
        
        # Vérifier l'impact sur la réservation
        reservation.refresh_from_db()
        print(f"\nRéservation après mise à jour:")
        print(f"  Status: {reservation.status}")
        print(f"  Is paid: {reservation.is_paid}")
        print(f"  Payment status: {reservation.payment_status}")
        
        # Créer la notification admin
        try:
            from payment_notification_service import PaymentNotificationService
            result = PaymentNotificationService.create_payment_notification(reservation, payment)
            print(f"✅ Notification admin créée: {result}")
        except Exception as e:
            print(f"❌ Erreur notification: {e}")
        
        # Vérifier les notifications existantes
        print(f"\n📊 Notifications admin:")
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM admin_notifications 
                WHERE admin_email = %s AND is_read = FALSE
            """, ['admin@example.com'])
            count = cursor.fetchone()[0]
            print(f"  Notifications non lues: {count}")
            
            cursor.execute("""
                SELECT * FROM admin_notifications 
                WHERE reservation_id = %s 
                ORDER BY created_at DESC 
                LIMIT 3
            """, [17])
            notifications = cursor.fetchall()
            
            for notif in notifications:
                print(f"  - {notif[4]} ({notif[6]})")
    
    else:
        print(f"❌ Aucun paiement trouvé pour la réservation 17")
        
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== TEST DU SYSTÈME ===")
print(f"1. Connectez-vous en admin: admin@example.com")
print(f"2. Allez sur: http://127.0.0.1:8000/notifications/")
print(f"3. Vous devriez voir la notification pour la réservation 17")
print(f"4. Allez sur: http://127.0.0.1:8000/reservations/17/")
print(f"5. Le bouton 'Confirmer la Réservation' devrait être visible")

print(f"\n=== ÉTATS ATTENDUS ===")
print(f"✅ Payment.status: 'paid'")
print(f"✅ Reservation.is_paid: True")
print(f"✅ Admin notifié")
print(f"✅ Bouton confirmation visible pour admin")
