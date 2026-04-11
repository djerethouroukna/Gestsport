#!/usr/bin/env python3
"""
Script de test pour valider les corrections du scanner
"""

import os
import sys
import django
import requests
import json
from datetime import datetime, timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from reservations.models import Reservation
from terrains.models import Terrain
from activities.models import Activity
from tickets.models import Ticket, Scan

User = get_user_model()

class ScannerTester:
    def __init__(self):
        self.api_base_url = "http://127.0.0.1:8000"
        self.api_token = "952f56a69dd6456297c6363d3f1836892eec9f24"
        self.scanner_id = "scanner_test_01"
        self.location = "Test Location"
        
        print("🔧 Initialisation du testeur de scanner")
        print(f"   API: {self.api_base_url}")
        print(f"   Scanner: {self.scanner_id}")
        print()
    
    def test_api_connection(self):
        """Test la connexion à l'API"""
        print("🌐 Test de connexion API...")
        
        try:
            url = f"{self.api_base_url}/tickets/api/scanner/status/"
            headers = {"Authorization": f"Token {self.api_token}"}
            params = {"scanner_id": self.scanner_id}
            
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API connectée - Status: {data.get('status', 'inconnu')}")
                return True
            else:
                print(f"❌ Erreur API: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            return False
    
    def create_test_ticket(self, hours_delta=0):
        """Crée un ticket de test"""
        print(f"🎫 Création ticket de test (delta: {hours_delta}h)...")
        
        try:
            # Récupérer ou créer les objets nécessaires
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.create_user(
                    email='test@example.com',
                    first_name='Test',
                    last_name='User',
                    role='player'
                )
            
            terrain = Terrain.objects.first()
            if not terrain:
                terrain = Terrain.objects.create(
                    name="Terrain Test",
                    description="Terrain pour tests",
                    capacity=10,
                    hourly_rate=20.0
                )
            
            activity = Activity.objects.first()
            if not activity:
                activity = Activity.objects.create(
                    title="Football Test",
                    description="Activity pour tests"
                )
            
            # Créer une réservation
            start_time = timezone.now() + timedelta(hours=hours_delta)
            end_time = start_time + timedelta(hours=1)
            
            reservation = Reservation.objects.create(
                user=user,
                terrain=terrain,
                activity=activity,
                start_time=start_time,
                end_time=end_time,
                status='confirmed',
                total_amount=20.0,
                paid_amount=20.0
            )
            
            # Créer le ticket
            ticket = Ticket.objects.create(
                reservation=reservation,
                is_valid=True,
                is_used=False
            )
            
            print(f"✅ Ticket créé: {ticket.ticket_number}")
            print(f"   Réservation: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}")
            
            return ticket
            
        except Exception as e:
            print(f"❌ Erreur création ticket: {e}")
            return None
    
    def test_scan_ticket(self, ticket_number, expected_status=None):
        """Test le scan d'un ticket"""
        print(f"🔍 Test scan ticket: {ticket_number}")
        
        try:
            url = f"{self.api_base_url}/tickets/api/scanner/scan/"
            headers = {
                "Authorization": f"Token {self.api_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "qr_data": ticket_number,
                "scanner_id": self.scanner_id,
                "location": self.location
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            print(f"   Status HTTP: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Ticket VALIDÉ: {result.get('message', 'Succès')}")
                    return "VALIDÉ"
                else:
                    error_code = result.get('error_code', 'UNKNOWN')
                    message = result.get('message', 'Erreur inconnue')
                    print(f"❌ Ticket REJETÉ: {error_code} - {message}")
                    return error_code
            else:
                print(f"❌ Erreur HTTP: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Détails: {error_data}")
                except:
                    pass
                return "ERROR"
                
        except Exception as e:
            print(f"❌ Erreur scan: {e}")
            return "ERROR"
    
    def run_tests(self):
        """Exécute tous les tests"""
        print("🚀 DÉMARRAGE DES TESTS DU SCANNER")
        print("=" * 50)
        
        # Test 1: Connexion API
        if not self.test_api_connection():
            print("❌ Impossible de se connecter à l'API - tests arrêtés")
            return
        
        print()
        
        # Test 2: Ticket valide (maintenant)
        print("📋 TEST 1: Ticket valide (réservation maintenant)")
        ticket_now = self.create_test_ticket(hours_delta=0)
        if ticket_now:
            result = self.test_scan_ticket(ticket_now.ticket_number)
            print(f"   Résultat attendu: VALIDÉ, Obtenu: {result}")
            print(f"   {'✅' if result == 'VALIDÉ' else '❌'} Test {'réussi' if result == 'VALIDÉ' else 'échoué'}")
        print()
        
        # Test 3: Ticket futur (dans 3 heures)
        print("📋 TEST 2: Ticket futur (réservation dans 3h)")
        ticket_future = self.create_test_ticket(hours_delta=3)
        if ticket_future:
            result = self.test_scan_ticket(ticket_future.ticket_number)
            print(f"   Résultat attendu: FUTURE_RESERVATION, Obtenu: {result}")
            print(f"   {'✅' if result == 'FUTURE_RESERVATION' else '❌'} Test {'réussi' if result == 'FUTURE_RESERVATION' else 'échoué'}")
        print()
        
        # Test 4: Ticket expiré (il y a 2 heures)
        print("📋 TEST 3: Ticket expiré (réservation il y a 2h)")
        ticket_expired = self.create_test_ticket(hours_delta=-2)
        if ticket_expired:
            # Forcer l'expiration en modifiant la réservation
            ticket_expired.reservation.end_time = timezone.now() - timedelta(hours=1)
            ticket_expired.reservation.save()
            
            result = self.test_scan_ticket(ticket_expired.ticket_number)
            print(f"   Résultat attendu: EXPIRED_RESERVATION, Obtenu: {result}")
            print(f"   {'✅' if result == 'EXPIRED_RESERVATION' else '❌'} Test {'réussi' if result == 'EXPIRED_RESERVATION' else 'échoué'}")
        print()
        
        # Test 5: Ticket déjà utilisé
        print("📋 TEST 4: Ticket déjà utilisé")
        ticket_used = self.create_test_ticket(hours_delta=0)
        if ticket_used:
            # Marquer le ticket comme utilisé
            ticket_used.is_used = True
            ticket_used.used_at = timezone.now()
            ticket_used.save()
            
            result = self.test_scan_ticket(ticket_used.ticket_number)
            print(f"   Résultat attendu: TICKET_ALREADY_USED, Obtenu: {result}")
            print(f"   {'✅' if result == 'TICKET_ALREADY_USED' else '❌'} Test {'réussi' if result == 'TICKET_ALREADY_USED' else 'échoué'}")
        print()
        
        # Test 6: Ticket non trouvé
        print("📋 TEST 5: Ticket non trouvé")
        result = self.test_scan_ticket("TICKET_INEXISTANT")
        print(f"   Résultat attendu: TICKET_NOT_FOUND, Obtenu: {result}")
        print(f"   {'✅' if result == 'TICKET_NOT_FOUND' else '❌'} Test {'réussi' if result == 'TICKET_NOT_FOUND' else 'échoué'}")
        print()
        
        print("🏁 TESTS TERMINÉS")
        print("=" * 50)

def main():
    """Fonction principale"""
    tester = ScannerTester()
    tester.run_tests()

if __name__ == "__main__":
    main()
