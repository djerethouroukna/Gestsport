#!/usr/bin/env python
"""
Script pour corriger les paiements qui sont restés en statut 'paid' 
alors que leur réservation est confirmée.
"""

import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from payments.models import Payment
from reservations.models import Reservation
from django.utils import timezone

def fix_paid_to_completed():
    """Corrige les paiements 'paid' vers 'completed' pour réservations confirmées"""
    
    print("🔧 Correction des paiements 'paid' vers 'completed'...")
    
    # Récupérer tous les paiements en statut 'paid'
    paid_payments = Payment.objects.filter(status='paid')
    print(f"📊 Trouvé {paid_payments.count()} paiements en statut 'paid'")
    
    corrected_count = 0
    
    for payment in paid_payments:
        try:
            reservation = payment.reservation
            
            # Vérifier si la réservation est confirmée
            if reservation and reservation.status == 'confirmed':
                print(f"✅ Paiement {payment.id} - Réservation {reservation.id} confirmée")
                print(f"   Montant: {payment.amount} FCFA")
                print(f"   Statut actuel: {payment.status} → completed")
                
                # Mettre à jour le paiement
                payment.status = 'completed'
                payment.processed_at = timezone.now()
                payment.save()
                
                corrected_count += 1
                print(f"   ✅ Paiement {payment.id} corrigé!")
                
            else:
                print(f"⏸️  Paiement {payment.id} - Réservation non confirmée (statut: {reservation.status if reservation else 'N/A'})")
                
        except Exception as e:
            print(f"❌ Erreur avec paiement {payment.id}: {e}")
    
    print(f"\n🎯 Résultat: {corrected_count} paiements corrigés sur {paid_payments.count()}")
    
    # Vérification finale
    remaining_paid = Payment.objects.filter(status='paid').count()
    print(f"📊 Paiements restants en 'paid': {remaining_paid}")
    
    completed_payments = Payment.objects.filter(status='completed').count()
    print(f"✅ Paiements en 'completed': {completed_payments}")

if __name__ == "__main__":
    fix_paid_to_completed()
