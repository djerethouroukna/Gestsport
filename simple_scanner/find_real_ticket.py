#!/usr/bin/env python3
# ==============================================================================
# TROUVER UN VRAI TICKET POUR TESTER LE SCANNER
# ==============================================================================

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation
from users.models import User
from django.utils import timezone

def find_real_ticket():
    """Trouve un ticket réel pour tester"""
    
    print("=" * 60)
    print("   RECHERCHE D'UN VRAI TICKET")
    print("=" * 60)
    
    try:
        # 1. Compter les tickets
        total_tickets = Ticket.objects.count()
        print(f"📊 Total tickets dans la base: {total_tickets}")
        
        if total_tickets == 0:
            print("❌ Aucun ticket trouvé dans la base")
            print("\nCréez d'abord des tickets via:")
            print("  1. Interface web de GestSport")
            print("  2. Script create_valid_ticket.py")
            return None
        
        # 2. Trouver un ticket valide (non utilisé)
        valid_tickets = Ticket.objects.filter(is_used=False)
        print(f"✅ Tickets valides (non utilisés): {valid_tickets.count()}")
        
        if valid_tickets.count() == 0:
            print("⚠️ Aucun ticket valide trouvé")
            print("Tous les tickets sont déjà utilisés")
            
            # Afficher les tickets utilisés
            used_tickets = Ticket.objects.filter(is_used=True)[:5]
            print("\n📋 Derniers tickets utilisés:")
            for ticket in used_tickets:
                print(f"  - {ticket.ticket_number} (utilisé le {ticket.used_at})")
            return None
        
        # 3. Prendre le premier ticket valide
        ticket = valid_tickets.first()
        
        print(f"\n🎫 TICKET TROUVÉ:")
        print(f"  Numéro: {ticket.ticket_number}")
        print(f"  Statut: {'Valide' if not ticket.is_used else 'Utilisé'}")
        print(f"  Créé le: {ticket.created_at}")
        
        if ticket.reservation:
            print(f"\n📋 RÉSERVATION ASSOCIÉE:")
            print(f"  Utilisateur: {ticket.reservation.user.get_full_name() or ticket.reservation.user.username}")
            print(f"  Terrain: {ticket.reservation.terrain.name}")
            print(f"  Début: {ticket.reservation.start_time}")
            print(f"  Fin: {ticket.reservation.end_time}")
            print(f"  Montant: {ticket.reservation.total_amount} FCFA")
        
        print(f"\n🎯 UTILISEZ CE NUMÉRO POUR TESTER:")
        print(f"  {ticket.ticket_number}")
        
        print("\n" + "=" * 60)
        print("✅ Ce ticket devrait donner une réponse 200 OK")
        print("=" * 60)
        
        return ticket.ticket_number
        
    except Exception as e:
        print(f"❌ Erreur recherche ticket: {e}")
        return None

def test_ticket_with_api(ticket_number):
    """Teste le ticket avec l'API"""
    
    print(f"\n🔄 TEST API AVEC: {ticket_number}")
    
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
            print("✅ SUCCÈS!")
            print(f"Response: {result}")
        else:
            print(f"❌ ERREUR: {response.status_code}")
            try:
                result = response.json()
                print(f"Response: {result}")
            except:
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Erreur requête: {e}")

if __name__ == "__main__":
    ticket = find_real_ticket()
    
    if ticket:
        test_ticket_with_api(ticket)
        
        print(f"\n🎯 MAINTENANT TESTEZ AVEC:")
        print(f"  1. Démarrez scanner_manual.py")
        print(f"  2. Saisissez: {ticket}")
        print(f"  3. Vous devriez voir: ✅ VALIDÉ")
    else:
        print("\n❌ Aucun ticket disponible pour le test")
        print("Créez d'abord des tickets dans votre système GestSport")
