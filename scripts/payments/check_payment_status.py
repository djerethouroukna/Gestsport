import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from reservations.models import Reservation
from payments.models import Payment

print("=== VÉRIFICATION STATUT PAIEMENT ===")

# Vérifier la réservation 13
try:
    reservation = Reservation.objects.get(id=13)
    print(f"Réservation 13:")
    print(f"  User: {reservation.user.email}")
    print(f"  Status: {reservation.status}")
    print(f"  Is paid: {reservation.is_paid}")
    print(f"  Payment status: {reservation.payment_status}")
    
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
                
                if session.payment_status == 'paid':
                    print(f"  ✅ PAIEMENT CONFIRMÉ PAR STRIPE")
                    
                    # Mettre à jour le statut du paiement
                    if payment.status != 'paid':
                        payment.status = 'paid'
                        payment.save()
                        print(f"  ✅ Payment status mis à jour à 'paid'")
                        
                    # Vérifier si la réservation est toujours pending
                    if reservation.status == 'pending':
                        print(f"  ⚠️  La réservation est toujours 'pending'")
                        print(f"  🔧 L'admin doit maintenant confirmer la réservation")
                        
                else:
                    print(f"  ❌ Paiement non confirmé par Stripe")
                    
            except Exception as e:
                print(f"  ❌ Erreur vérification session Stripe: {e}")
    
    print(f"\n=== ÉTATS ATTENDUS ===")
    print(f"Après paiement réussi:")
    print(f"  - Payment.status = 'paid' ✅")
    print(f"  - Reservation.status = 'pending' (en attente confirmation admin) ⚠️")
    print(f"  - Reservation.is_paid = True ✅")
    
    print(f"\n=== ACTIONS NÉCESSAIRES ===")
    print(f"1. Admin doit se connecter")
    print(f"2. Admin doit aller sur la réservation 13")
    print(f"3. Admin doit cliquer sur 'Confirmer la Réservation'")
    print(f"4. Après confirmation, coach pourra générer le ticket")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
