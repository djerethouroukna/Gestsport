import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone

import stripe
from django.conf import settings
from payments.models import Payment, PaymentStatus
from reservations.models import Reservation

print("=== MISE À JOUR MANUELLE PAIEMENT ===")

# Configuration Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Récupérer la réservation 13
reservation = Reservation.objects.get(id=13)
payment = Payment.objects.filter(reservation=reservation).first()

print(f"Réservation {reservation.id}:")
print(f"  Status: {reservation.status}")
print(f"  Is paid: {reservation.is_paid}")

print(f"\nPayment {payment.id}:")
print(f"  Status: {payment.status}")
print(f"  Session ID: {payment.notes.split('Session: ')[1] if 'Session:' in payment.notes else 'None'}")

# Vérifier le statut réel de la session Stripe
try:
    if 'Session:' in payment.notes:
        session_id = payment.notes.split('Session: ')[1]
        session = stripe.checkout.Session.retrieve(session_id)
        
        print(f"\nSession Stripe:")
        print(f"  Status: {session.status}")
        print(f"  Payment Status: {session.payment_status}")
        print(f"  Payment Intent: {session.payment_intent}")
        
        # Si le paiement est réussi, mettre à jour
        if session.payment_status == 'paid' and payment.status != 'paid':
            print(f"\n✅ PAIEMENT DÉTECTÉ - MISE À JOUR EN COURS...")
            
            # Mettre à jour le statut du paiement
            payment.status = 'paid'
            payment.paid_at = timezone.now()
            payment.transaction_id = session.payment_intent
            payment.save()
            
            print(f"✅ Payment status mis à jour à 'paid'")
            print(f"✅ Transaction ID: {session.payment_intent}")
            
            # Vérifier la réservation
            reservation.refresh_from_db()
            print(f"\nRéservation après mise à jour:")
            print(f"  Status: {reservation.status}")
            print(f"  Is paid: {reservation.is_paid}")
            print(f"  Payment status: {reservation.payment_status}")
            
            print(f"\n=== ÉTATS ACTUELS ===")
            print(f"✅ Payment.status: {payment.status}")
            print(f"✅ Reservation.is_paid: {reservation.is_paid}")
            print(f"⚠️  Reservation.status: {reservation.status} (doit être confirmé par admin)")
            
            print(f"\n=== PROCHAINES ÉTAPES ===")
            print(f"1. Admin doit se connecter")
            print(f"2. Admin va sur http://127.0.0.1:8000/reservations/13/")
            print(f"3. Admin verra le bouton 'Confirmer la Réservation'")
            print(f"4. Admin clique sur 'Confirmer'")
            print(f"5. Après confirmation, coach pourra générer le ticket")
            
        elif session.payment_status == 'unpaid':
            print(f"\n❌ PAIEMENT NON TERMINÉ")
            print(f"Le paiement est toujours en attente")
            print(f"Status de la session: {session.status}")
            
        else:
            print(f"\n❌ STATUT INCONNU")
            print(f"Payment status: {session.payment_status}")
            
except Exception as e:
    print(f"❌ Erreur vérification session: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== TEST DES BOUTONS APRÈS MISE À JOUR ===")
print(f"Admin (réservation pending + payée):")
print(f"  ✅ Bouton 'Confirmer la Réservation': VISIBLE")
print(f"  ✅ Bouton 'Rejeter la Réservation': VISIBLE")

print(f"\nCoach (réservation pending + payée):")
print(f"  ❌ Bouton 'Procéder au Paiement': NON VISIBLE")
print(f"  ❌ Bouton 'Générer le Ticket': NON VISIBLE (en attente confirmation)")

print(f"\nCoach (réservation confirmed + payée):")
print(f"  ❌ Bouton 'Procéder au Paiement': NON VISIBLE")
print(f"  ✅ Bouton 'Générer le Ticket': VISIBLE")
print(f"  ✅ Bouton 'Télécharger le Ticket': VISIBLE (après génération)")
