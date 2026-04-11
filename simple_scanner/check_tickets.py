#!/usr/bin/env python3
# ==============================================================================
# VÉRIFICATION SIMPLE DES TICKETS SANS DJANGO
# ==============================================================================

import requests
import json

def check_api_status():
    """Vérifie le statut de l'API"""
    
    print("=" * 60)
    print("   VÉRIFICATION DE L'API GESTSPORT")
    print("=" * 60)
    
    try:
        url = "http://127.0.0.1:8000/tickets/api/scanner/status/"
        headers = {"Authorization": "Token a9dc052f48d8098984e2f916673b51ed2e364929"}
        params = {"scanner_id": "scanner_test_01"}
        
        response = requests.get(url, headers=headers, params=params, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API accessible")
            print(f"Scanner ID: {result.get('scanner_id')}")
            print(f"Status: {result.get('status')}")
            print(f"Scans aujourd'hui: {result.get('scans_today', 0)}")
            print(f"Total scans: {result.get('total_scans', 0)}")
            return True
        else:
            print(f"❌ Erreur API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur connexion API: {e}")
        return False

def test_ticket_formats():
    """Teste différents formats de tickets"""
    
    print("\n" + "=" * 60)
    print("   TEST DE DIFFÉRENTS FORMATS DE TICKETS")
    print("=" * 60)
    
    # Formats de tickets à tester
    test_tickets = [
        "TKT-123456789",
        "TKT-ABC123DEF456", 
        "TKT-20240217123456",
        "TKT-TEST123456",
        "TKT-71992AD03C184388",
        "TK_Ajfrvnvkrcd",
        "1234567890",
        "ABC-123-DEF",
        "TICKET-001"
    ]
    
    url = "http://127.0.0.1:8000/tickets/api/scanner/scan/"
    headers = {
        "Authorization": "Token a9dc052f48d8098984e2f916673b51ed2e364929",
        "Content-Type": "application/json"
    }
    
    for ticket in test_tickets:
        print(f"\n🎫 Test: {ticket}")
        
        data = {
            "qr_data": ticket,
            "scanner_id": "scanner_test_01",
            "location": "Test Location"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ SUCCÈS: {result.get('message')}")
                    print(f"   🎯 TROUVÉ! Utilisez ce ticket: {ticket}")
                else:
                    print(f"❌ REJETÉ: {result.get('message')}")
            elif response.status_code == 404:
                print(f"❌ NON TROUVÉ (404): Ticket n'existe pas")
            elif response.status_code == 400:
                print(f"❌ MAUVAIS FORMAT (400): Format invalide")
            else:
                print(f"⚠️ ERREUR {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ ERREUR REQUÊTE: {e}")

def explain_error_codes():
    """Explique les codes d'erreur"""
    
    print("\n" + "=" * 60)
    print("   EXPLICATION DES CODES D'ERREUR")
    print("=" * 60)
    
    explanations = {
        "200": "✅ SUCCÈS - Ticket valide et traité",
        "400": "❌ BAD REQUEST - Format du ticket invalide",
        "401": "❌ UNAUTHORIZED - Token API incorrect",
        "403": "❌ FORBIDDEN - Permissions insuffisantes",
        "404": "❌ NOT FOUND - Ticket non trouvé dans la base",
        "500": "❌ SERVER ERROR - Erreur interne du serveur",
        "502": "❌ BAD GATEWAY - Serveur indisponible",
        "503": "❌ SERVICE UNAVAILABLE - Maintenance en cours"
    }
    
    for code, explanation in explanations.items():
        print(f"{code}: {explanation}")
    
    print(f"\n🎯 POUR ÉVITER LES ERREURS:")
    print(f"   1. Utilisez un ticket qui existe vraiment dans votre base")
    print(f"   2. Vérifiez le format attendu par votre API")
    print(f"   3. Assurez-vous que le serveur Django est démarré")
    print(f"   4. Vérifiez que le token API est correct")

def main():
    """Fonction principale"""
    
    # 1. Vérifier l'API
    if not check_api_status():
        print("\n❌ L'API n'est pas accessible. Démarrez le serveur Django:")
        print("   cd e:/backend")
        print("   python manage.py runserver")
        return
    
    # 2. Tester différents formats
    test_ticket_formats()
    
    # 3. Expliquer les erreurs
    explain_error_codes()
    
    print(f"\n" + "=" * 60)
    print("🎯 CONCLUSION:")
    print("=" * 60)
    print("Les erreurs 400 et 404 sont NORMALES avec des tickets de test.")
    print("Pour obtenir un succès (200), utilisez un VRAI ticket de votre base.")
    print("=" * 60)

if __name__ == "__main__":
    main()
