import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone

from reservations.models import Reservation
from payments.models import Payment
from users.models import User

print("=== DIAGNOSTIC RÉSERVATION 17 ===")

# Vérifier la réservation 17
try:
    reservation = Reservation.objects.get(id=17)
    print(f"Réservation 17:")
    print(f"  User: {reservation.user.email}")
    print(f"  Status: {reservation.status}")
    print(f"  Is paid: {reservation.is_paid}")
    print(f"  Payment status: {reservation.payment_status}")
    print(f"  Total amount: {reservation.total_amount}")
    print(f"  Created: {reservation.created_at}")
    
    # Vérifier les paiements
    payments = Payment.objects.filter(reservation=reservation)
    print(f"\nPaiements trouvés: {payments.count()}")
    
    for payment in payments:
        print(f"\nPayment {payment.id}:")
        print(f"  Status: {payment.status}")
        print(f"  Amount: {payment.amount} {payment.currency}")
        print(f"  Is paid: {payment.is_paid}")
        print(f"  Notes: {payment.notes}")
        print(f"  Created: {payment.created_at}")
        print(f"  Updated: {payment.updated_at}")
        
        # Vérifier si c'est un paiement Stripe
        if 'Session:' in payment.notes:
            session_id = payment.notes.split('Session: ')[1]
            print(f"  Session ID: {session_id}")
            
            # Vérifier le statut de la session Stripe
            try:
                import stripe
                from django.conf import settings
                stripe.api_key = settings.STRIPE_SECRET_KEY
                
                session = stripe.checkout.Session.retrieve(session_id)
                print(f"  Stripe session status: {session.status}")
                print(f"  Stripe payment status: {session.payment_status}")
                print(f"  Stripe payment intent: {session.payment_intent}")
                
                if session.payment_status == 'paid':
                    print(f"  ✅ PAIEMENT CONFIRMÉ PAR STRIPE")
                    
                    # Mettre à jour le statut du paiement
                    if payment.status != 'paid':
                        payment.status = 'paid'
                        payment.paid_at = timezone.now()
                        payment.transaction_id = session.payment_intent
                        payment.save()
                        print(f"  ✅ Payment status mis à jour à 'paid'")
                        
                        # Vérifier la réservation
                        reservation.refresh_from_db()
                        print(f"\nRéservation après mise à jour:")
                        print(f"  Status: {reservation.status}")
                        print(f"  Is paid: {reservation.is_paid}")
                        
                        # Créer notification admin
                        from payment_notification_service import PaymentNotificationService
                        result = PaymentNotificationService.create_payment_notification(reservation, payment)
                        print(f"  ✅ Notification admin créée: {result}")
                        
                elif session.payment_status == 'unpaid':
                    print(f"  ❌ PAIEMENT NON TERMINÉ")
                    print(f"  Status de la session: {session.status}")
                    
                else:
                    print(f"  ❌ STATUT INCONNU")
                    print(f"  Payment status: {session.payment_status}")
                    
            except Exception as e:
                print(f"  ❌ Erreur vérification session Stripe: {e}")
    
    # Vérifier si la réservation devrait être confirmée
    print(f"\n🔍 État attendu:")
    print(f"  Si paiement réussi:")
    print(f"    - Payment.status = 'paid'")
    print(f"    - Reservation.is_paid = True")
    print(f"    - Admin doit recevoir notification")
    print(f"    - Admin doit pouvoir confirmer")
    
    print(f"\n📊 État actuel vs attendu:")
    print(f"  Payment.status: {payments.first().status if payments.exists() else 'None'} (attendu: 'paid')")
    print(f"  Reservation.status: {reservation.status} (attendu: 'pending' si payé)")
    print(f"  Reservation.is_paid: {reservation.is_paid} (attendu: True)")
    
except Reservation.DoesNotExist:
    print(f"❌ Réservation 17 non trouvée")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== TEST CRÉATION NOTIFICATION MANUELLE ===")
try:
    reservation = Reservation.objects.get(id=17)
    payment = Payment.objects.filter(reservation=reservation).first()
    
    if payment and payment.status == 'paid':
        from payment_notification_service import PaymentNotificationService
        result = PaymentNotificationService.create_payment_notification(reservation, payment)
        print(f"✅ Notification manuelle créée: {result}")
    else:
        print(f"❌ Impossible de créer notification: payment non trouvé ou non payé")
        
except Exception as e:
    print(f"❌ Erreur création notification: {e}")

print(f"\n=== VÉRIFICATION NOTIFICATIONS ADMIN ===")
try:
    from payment_notification_service import PaymentNotificationService
    from users.models import User
    
    admin = User.objects.filter(role='admin').first()
    if admin:
        count = PaymentNotificationService.get_unread_count(admin.email)
        print(f"Notifications non lues pour {admin.email}: {count}")
    else:
        print("❌ Aucun admin trouvé")
        
except Exception as e:
    print(f"❌ Erreur vérification notifications: {e}")
