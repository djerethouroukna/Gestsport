#!/usr/bin/env python3
"""
Script de diagnostic pour comprendre pourquoi le statut de paiement reste "non payé"
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
from django.contrib.auth import get_user_model

User = get_user_model()

class PaymentStatusDebugger:
    def __init__(self):
        print("🔍 **Diagnostic du statut de paiement**")
        print("=" * 50)
    
    def check_recent_reservations(self):
        """Vérifie les réservations récentes et leur statut de paiement"""
        print("\n📋 **Réservations récentes (dernières 24h):**")
        
        recent_reservations = Reservation.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).order_by('-created_at')
        
        if not recent_reservations:
            print("   Aucune réservation récente trouvée")
            return
        
        for res in recent_reservations:
            print(f"\n   📅 Réservation #{res.id}")
            print(f"      Utilisateur: {res.user}")
            print(f"      Terrain: {res.terrain}")
            print(f"      Date: {res.start_time}")
            print(f"      Statut: {res.status}")
            print(f"      💰 Statut paiement: {res.payment_status}")
            print(f"      💳 Méthode paiement: {res.payment_method}")
            print(f"      📅 Date paiement: {res.payment_date}")
            print(f"      🆔 Transaction ID: {res.transaction_id}")
            print(f"      💵 Montant: {res.total_amount}")
            
            # Vérifier les paiements associés
            payments = Payment.objects.filter(reservation=res)
            for payment in payments:
                print(f"         💳 Paiement #{payment.id}: {payment.status} - {payment.amount}")
                print(f"            Créé: {payment.created_at}")
                print(f"            Payé le: {payment.paid_at}")
                print(f"            Notes: {payment.notes}")
    
    def check_pending_payments(self):
        """Vérifie les paiements en attente"""
        print("\n⏳ **Paiements en attente:**")
        
        pending_payments = Payment.objects.filter(status='pending').order_by('-created_at')
        
        if not pending_payments:
            print("   Aucun paiement en attente")
            return
        
        for payment in pending_payments:
            print(f"\n   💳 Paiement #{payment.id}")
            print(f"      Réservation: #{payment.reservation.id}")
            print(f"      Utilisateur: {payment.user}")
            print(f"      Montant: {payment.amount}")
            print(f"      Statut: {payment.status}")
            print(f"      Créé: {payment.created_at}")
            print(f"      Notes: {payment.notes}")
            
            # Vérifier la réservation associée
            res = payment.reservation
            print(f"      📅 Réservation statut paiement: {res.payment_status}")
    
    def check_webhook_logs(self):
        """Vérifie les logs récents pour les webhooks"""
        print("\n🕷️ **Vérification des logs de webhook:**")
        
        import logging
        from django.conf import settings
        
        # Chercher les logs de paiement récents
        log_file = 'logs/scanner.log'  # Adapter selon votre config
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            webhook_lines = []
            for line in lines[-100:]:  # Dernières 100 lignes
                if 'WEBHOOK' in line or 'STRIPE' in line:
                    webhook_lines.append(line.strip())
            
            if webhook_lines:
                print("   Logs récents de webhook/Stripe:")
                for line in webhook_lines[-10:]:  # Derniers 10 logs
                    print(f"      {line}")
            else:
                print("   Aucun log de webhook trouvé récemment")
                
        except FileNotFoundError:
            print("   Fichier de log non trouvé")
        except Exception as e:
            print(f"   Erreur lecture logs: {e}")
    
    def check_stripe_config(self):
        """Vérifie la configuration Stripe"""
        print("\n⚙️ **Configuration Stripe:**")
        
        from django.conf import settings
        
        print(f"   🔑 Publishable Key: {settings.STRIPE_PUBLISHABLE_KEY[:20]}...")
        print(f"   🔐 Secret Key: {settings.STRIPE_SECRET_KEY[:20]}...")
        print(f"   🕷️ Webhook Secret: {settings.STRIPE_WEBHOOK_SECRET[:20]}...")
        
        # Vérifier si les clés sont en mode test
        is_test = 'test' in settings.STRIPE_PUBLISHABLE_KEY
        print(f"   🧪 Mode test: {'Oui' if is_test else 'Non'}")
    
    def simulate_webhook_test(self):
        """Simule un test de webhook"""
        print("\n🧪 **Test de simulation de webhook:**")
        
        # Trouver une réservation avec paiement en attente
        pending_payment = Payment.objects.filter(status='pending').first()
        
        if not pending_payment:
            print("   Aucun paiement en attente à tester")
            return
        
        print(f"   💳 Test avec paiement #{pending_payment.id}")
        
        # Simuler la mise à jour manuelle
        try:
            reservation = pending_payment.reservation
            
            # Mettre à jour le paiement
            pending_payment.status = 'paid'
            pending_payment.paid_at = timezone.now()
            pending_payment.save()
            
            # Mettre à jour la réservation
            reservation.payment_status = 'paid'
            reservation.payment_method = 'card'
            reservation.payment_date = timezone.now()
            reservation.transaction_id = 'test_simulation_' + str(pending_payment.id)
            reservation.save()
            
            print(f"   ✅ Simulation réussie:")
            print(f"      Paiement #{pending_payment.id} mis à jour: paid")
            print(f"      Réservation #{reservation.id} mise à jour: paid")
            
        except Exception as e:
            print(f"   ❌ Erreur simulation: {e}")
    
    def check_webhook_url(self):
        """Vérifie l'URL du webhook"""
        print("\n🌐 **URL du Webhook:**")
        
        from django.urls import reverse
        
        try:
            webhook_url = reverse('payments:stripe_webhook')
            print(f"   📍 URL interne: {webhook_url}")
            print(f"   🌍 URL complète: http://127.0.0.1:8000/payments/stripe/webhook/")
            print(f"   🔒 URL HTTPS (production): https://votreserveur.com/payments/stripe/webhook/")
        except Exception as e:
            print(f"   ❌ Erreur URL webhook: {e}")
    
    def run_diagnostic(self):
        """Exécute le diagnostic complet"""
        print("🚀 **Démarrage du diagnostic complet**")
        
        self.check_stripe_config()
        self.check_webhook_url()
        self.check_recent_reservations()
        self.check_pending_payments()
        self.check_webhook_logs()
        self.simulate_webhook_test()
        
        print("\n" + "=" * 50)
        print("🎯 **Recommandations:**")
        print("1. Vérifiez que le webhook Stripe est configuré dans votre dashboard Stripe")
        print("2. L'URL du webhook doit être: https://votreserveur.com/payments/stripe/webhook/")
        print("3. Le webhook secret doit correspondre à celui dans settings.py")
        print("4. Assurez-vous que le serveur est accessible publiquement pour les webhooks")
        print("5. Vérifiez les logs Django pour les erreurs de webhook")
        print("\n🔧 **Si problème persiste:**")
        print("- Utilisez la simulation manuelle (ci-dessus) pour tester")
        print("- Vérifiez les logs Stripe dans votre dashboard")
        print("- Testez avec Stripe CLI: stripe listen --forward-to localhost:8000/payments/stripe/webhook/")

def main():
    debugger = PaymentStatusDebugger()
    debugger.run_diagnostic()

if __name__ == "__main__":
    main()
