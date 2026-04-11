#!/usr/bin/env python3
# ====================================================================
# CRÉATION D'UN TICKET DE TEST POUR LE SCANNER
# ====================================================================

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation
from users.models import User
from terrains.models import Terrain
from django.utils import timezone
from datetime import timedelta

def create_test_ticket():
    """Crée un ticket de test pour le scanner"""
    
    print("=" * 60)
    print("   CRÉATION D'UN TICKET DE TEST")
    print("=" * 60)
    
    try:
        # 1. Récupérer ou créer un utilisateur
        user = User.objects.first()
        if not user:
            print("❌ Aucun utilisateur trouvé")
            return None
        
        print(f"✅ Utilisateur: {user.get_full_name() or user.username}")
        
        # 2. Récupérer ou créer un terrain
        terrain = Terrain.objects.first()
        if not terrain:
            print("❌ Aucun terrain trouvé")
            return None
        
        print(f"✅ Terrain: {terrain.name}")
        
        # 3. Créer une réservation valide
        reservation, created = Reservation.objects.get_or_create(
            user=user,
            terrain=terrain,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
            defaults={
                'status': 'confirmed',
                'total_amount': 50.00
            }
        )
        
        if created:
            print(f"✅ Réservation créée: {reservation.id}")
        else:
            print(f"✅ Réservation existante: {reservation.id}")
        
        # 4. Créer un ticket valide
        ticket_number = f"TKT-TEST-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        ticket, created = Ticket.objects.get_or_create(
            reservation=reservation,
            defaults={
                'ticket_number': ticket_number,
                'is_used': False
            }
        )
        
        if created:
            print(f"✅ Ticket créé: {ticket.ticket_number}")
            ticket.generate_qr_code()
            print(f"✅ QR code généré")
        else:
            print(f"✅ Ticket existant: {ticket.ticket_number}")
        
        print("\n" + "=" * 60)
        print("🎯 TICKET DE TEST CRÉÉ")
        print("=" * 60)
        print(f"Numéro: {ticket.ticket_number}")
        print(f"Utilisateur: {user.get_full_name() or user.username}")
        print(f"Terrain: {terrain.name}")
        print(f"Début: {reservation.start_time}")
        print(f"Fin: {reservation.end_time}")
        print(f"Durée: 2 heures")
        print(f"Statut: {'Valide' if not ticket.is_used else 'Utilisé'}")
        print("=" * 60)
        
        return ticket.ticket_number
        
    except Exception as e:
        print(f"❌ Erreur création ticket: {e}")
        return None

def test_scan_with_real_ticket():
    """Test le scan avec le ticket créé"""
    
    ticket_number = create_test_ticket()
    
    if not ticket_number:
        print("❌ Impossible de créer le ticket de test")
        return
    
    print(f"\n🔄 Test du scan avec le ticket: {ticket_number}")
    
    import requests
    
    url = "http://127.0.0.1:8000/tickets/api/scanner/scan/"
    headers = {
        "Authorization": "Token a9dc052f48d8098984e2f916673b51ed2e364929",
        "Content-Type": "application/json"
    }
    
    data = {
        "qr_data": ticket_number,
        "scanner_id": "scanner_test_01",
        "location": "Test Location"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Scan réussi!")
            print(f"Response: {result}")
        else:
            print(f"❌ Erreur scan: {response.status_code}")
            print(f"Response: {response.json()}")
            
    except Exception as e:
        print(f"❌ Erreur scan: {e}")

if __name__ == "__main__":
    test_scan_with_real_ticket()
