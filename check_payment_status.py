#!/usr/bin/env python3
"""
Script simple pour verifier le statut de paiement
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from reservations.models import Reservation
from payments.models import Payment

def check_status():
    """Verifie le statut actuel"""
    
    print("=== Verification du statut de paiement ===")
    
    try:
        # Récupérer la réservation #51
        reservation = Reservation.objects.get(id=51)
        print(f"Reservation #{reservation.id}:")
        print(f"  Statut: {reservation.status}")
        print(f"  Statut paiement: {reservation.payment_status}")
        print(f"  Methode paiement: {reservation.payment_method}")
        print(f"  Date paiement: {reservation.payment_date}")
        print(f"  Transaction ID: {reservation.transaction_id}")
        print(f"  Montant: {reservation.total_amount}")
        
        # Récupérer le paiement associé
        payment = Payment.objects.filter(reservation=reservation).first()
        if payment:
            print(f"\nPaiement #{payment.id}:")
            print(f"  Statut: {payment.status}")
            print(f"  Montant: {payment.amount}")
            print(f"  Cree le: {payment.created_at}")
            print(f"  Paye le: {payment.paid_at}")
            print(f"  Notes: {payment.notes}")
        
        print(f"\n--- Resultat ---")
        if reservation.payment_status == 'paid':
            print("✓ Le statut de paiement est correct: PAID")
        else:
            print("✗ Le statut de paiement est incorrect:", reservation.payment_status)
            
    except Reservation.DoesNotExist:
        print("Reservation #51 non trouvee")
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    check_status()
