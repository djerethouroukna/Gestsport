#!/usr/bin/env python3
"""
Script pour corriger manuellement le statut de paiement de la réservation #51
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

def fix_payment_status():
    """Corrige le statut de paiement de la réservation #51"""
    
    print("=== Correction du statut de paiement ===")
    
    try:
        # Récupérer la réservation #51
        reservation = Reservation.objects.get(id=51)
        print(f"Réservation #{reservation.id} trouvée")
        print(f"  Utilisateur: {reservation.user}")
        print(f"  Terrain: {reservation.terrain}")
        print(f"  Montant: {reservation.total_amount}")
        print(f"  Statut actuel: {reservation.payment_status}")
        
        # Récupérer le paiement associé
        payment = Payment.objects.filter(reservation=reservation).first()
        if payment:
            print(f"Paiement #{payment.id} trouvé")
            print(f"  Statut actuel: {payment.status}")
            print(f"  Créé le: {payment.created_at}")
        else:
            print("Aucun paiement trouvé")
            return
        
        # Mettre à jour le paiement
        payment.status = 'paid'
        payment.paid_at = timezone.now()
        payment.save()
        print("✅ Paiement mis à jour: paid")
        
        # Mettre à jour la réservation
        reservation.payment_status = 'paid'
        reservation.payment_method = 'card'
        reservation.payment_date = timezone.now()
        reservation.transaction_id = 'cs_test_a1fPuu7eZ1454CIJkVnb2PwBnIef5BHBOoKuNDOqmXAHaaUu3XZ7eNoP2B'
        reservation.save()
        print("✅ Réservation mise à jour: paid")
        
        # Vérification
        reservation.refresh_from_db()
        payment.refresh_from_db()
        
        print(f"\n--- Vérification ---")
        print(f"Réservation #{reservation.id}:")
        print(f"  Statut paiement: {reservation.payment_status}")
        print(f"  Méthode paiement: {reservation.payment_method}")
        print(f"  Date paiement: {reservation.payment_date}")
        print(f"  Transaction ID: {reservation.transaction_id}")
        
        print(f"\nPaiement #{payment.id}:")
        print(f"  Statut: {payment.status}")
        print(f"  Payé le: {payment.paid_at}")
        
        print(f"\n✅ Correction terminée avec succès !")
        
        # Créer une facture si nécessaire
        try:
            from payments.invoice_service import InvoiceService
            invoice = InvoiceService.create_invoice_for_payment(payment)
            if invoice:
                print(f"✅ Facture créée: {invoice.invoice_number}")
            else:
                print("ℹ️ Facture déjà existante")
        except Exception as e:
            print(f"⚠️ Erreur création facture: {e}")
        
    except Reservation.DoesNotExist:
        print("❌ Réservation #51 non trouvée")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    fix_payment_status()
