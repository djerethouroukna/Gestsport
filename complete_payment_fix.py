#!/usr/bin/env python3
"""
Script pour corriger completement la reservation #51
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

def complete_fix():
    """Correction complete de la reservation"""
    
    print("=== Correction complete de la reservation ===")
    
    try:
        # Récupérer la réservation #51
        reservation = Reservation.objects.get(id=51)
        print(f"Reservation #{reservation.id} avant correction:")
        print(f"  Statut: {reservation.status}")
        print(f"  Statut paiement: {reservation.payment_status}")
        print(f"  Methode paiement: '{reservation.payment_method}'")
        print(f"  Date paiement: {reservation.payment_date}")
        print(f"  Transaction ID: '{reservation.transaction_id}'")
        
        # Mettre à jour la réservation completement
        reservation.payment_method = 'card'
        reservation.payment_date = timezone.now()
        reservation.transaction_id = 'cs_test_a1fPuu7eZ1454CIJkVnb2PwBnIef5BHBOoKuNDOqmXAHaaUu3XZ7eNoP2B'
        
        # Confirmer la réservation si le statut est toujours pending
        if reservation.status == 'pending':
            reservation.status = 'confirmed'
        
        reservation.save()
        
        print(f"\nReservation #{reservation.id} apres correction:")
        print(f"  Statut: {reservation.status}")
        print(f"  Statut paiement: {reservation.payment_status}")
        print(f"  Methode paiement: '{reservation.payment_method}'")
        print(f"  Date paiement: {reservation.payment_date}")
        print(f"  Transaction ID: '{reservation.transaction_id}'")
        
        print(f"\nCorrection terminee avec succes!")
        
        # Creer une facture
        try:
            payment = Payment.objects.filter(reservation=reservation).first()
            if payment:
                from payments.invoice_service import InvoiceService
                invoice = InvoiceService.create_invoice_for_payment(payment)
                if invoice:
                    print(f"Facture creee: {invoice.invoice_number}")
                else:
                    print("Facture deja existante")
        except Exception as e:
            print(f"Erreur creation facture: {e}")
            
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    complete_fix()
