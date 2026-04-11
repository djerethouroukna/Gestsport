#!/usr/bin/env python3
"""
Script de test pour vérifier l'intégration audit logging du scanner
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from audit.models import AuditLog

User = get_user_model()

class AuditScannerTester:
    def __init__(self):
        self.api_base_url = "http://127.0.0.1:8000"
        self.api_token = "952f56a69dd6456297c6363d3f1836892eec9f24"
        
        print("🔧 Test d'intégration Audit Logging - Scanner")
        print(f"   API: {self.api_base_url}")
        print()
    
    def test_audit_api_connection(self):
        """Test la connexion à l'API d'audit"""
        print("🌐 Test connexion API Audit...")
        
        try:
            url = f"{self.api_base_url}/audit/api/log/"
            headers = {
                "Authorization": f"Token {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Test data
            test_data = {
                "action": "SCAN",
                "model_name": "Ticket",
                "object_repr": "Ticket TEST-123456",
                "changes": {
                    "scan_result": "TEST",
                    "scanner_id": "test_scanner",
                    "location": "Test Location"
                },
                "metadata": {
                    "scanner_type": "test",
                    "ticket_number": "TEST-123456",
                    "test_timestamp": datetime.now().isoformat()
                }
            }
            
            response = requests.post(url, headers=headers, json=test_data, timeout=5)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 201:
                result = response.json()
                print(f"   ✅ Audit API fonctionne: {result.get('message', 'Succès')}")
                print(f"   Audit ID: {result.get('audit_id', 'N/A')}")
                return True
            else:
                print(f"   ❌ Erreur API: {response.status_code}")
                try:
                    error = response.json()
                    print(f"   Détails: {error}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"   ❌ Erreur connexion: {e}")
            return False
    
    def check_audit_logs(self):
        """Vérifie les logs d'audit existants"""
        print("📋 Vérification logs d'audit...")
        
        try:
            # Compter les logs de scan
            scan_logs = AuditLog.objects.filter(action='SCAN').count()
            total_logs = AuditLog.objects.count()
            
            print(f"   Total logs d'audit: {total_logs}")
            print(f"   Logs de scan: {scan_logs}")
            
            # Afficher les 5 derniers logs de scan
            recent_scans = AuditLog.objects.filter(action='SCAN').order_by('-timestamp')[:5]
            
            if recent_scans:
                print("   📝 Derniers scans enregistrés:")
                for log in recent_scans:
                    user_str = log.user.email if log.user else "Système"
                    changes = log.changes or {}
                    scan_result = changes.get('scan_result', 'N/A')
                    scanner_id = changes.get('scanner_id', 'N/A')
                    print(f"      - {user_str} | {scan_result} | {scanner_id} | {log.object_repr}")
            else:
                print("   ℹ️ Aucun log de scan trouvé")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Erreur lecture logs: {e}")
            return False
    
    def simulate_scan_log(self):
        """Simule un enregistrement de scan"""
        print("🔍 Simulation enregistrement scan...")
        
        try:
            url = f"{self.api_base_url}/audit/api/log/"
            headers = {
                "Authorization": f"Token {self.api_token}",
                "Content-Type": "application/json"
            }
            
            # Simuler différents types de scan
            test_scans = [
                {
                    "ticket_number": "TKT-VALID-001",
                    "scan_result": "VALIDÉ",
                    "details": {
                        "terrain_name": "Terrain A",
                        "user_name": "Jean Test",
                        "date_formatted": "04/03/2026 14:00"
                    }
                },
                {
                    "ticket_number": "TKT-FUTURE-002",
                    "scan_result": "RÉSERVATION FUTURE",
                    "details": {
                        "error_code": "FUTURE_RESERVATION",
                        "reservation_datetime": "2026-03-05 15:00:00"
                    }
                },
                {
                    "ticket_number": "TKT-USED-003",
                    "scan_result": "DÉJÀ UTILISÉ",
                    "details": {
                        "error_code": "TICKET_ALREADY_USED",
                        "used_at": "2026-03-04 12:00:00"
                    }
                }
            ]
            
            for i, scan in enumerate(test_scans, 1):
                print(f"   Test {i}: {scan['scan_result']}")
                
                audit_data = {
                    "action": "SCAN",
                    "model_name": "Ticket",
                    "object_repr": f"Ticket {scan['ticket_number']}",
                    "changes": {
                        "scan_result": scan['scan_result'],
                        "scanner_id": "scanner_manual_01",
                        "location": "Entrée Principale",
                        "scan_details": scan['details']
                    },
                    "metadata": {
                        "scanner_type": "manual",
                        "ticket_number": scan['ticket_number'],
                        "test_mode": True,
                        "scan_timestamp": datetime.now().isoformat()
                    }
                }
                
                response = requests.post(url, headers=headers, json=audit_data, timeout=5)
                
                if response.status_code == 201:
                    result = response.json()
                    print(f"      ✅ Enregistré: {result.get('audit_id', 'N/A')}")
                else:
                    print(f"      ❌ Erreur: {response.status_code}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Erreur simulation: {e}")
            return False
    
    def run_tests(self):
        """Exécute tous les tests"""
        print("🚀 DÉMARRAGE DES TESTS D'AUDIT SCANNER")
        print("=" * 50)
        
        # Test 1: Connexion API Audit
        if not self.test_audit_api_connection():
            print("❌ API Audit inaccessible - tests arrêtés")
            return
        
        print()
        
        # Test 2: Vérification logs existants
        self.check_audit_logs()
        print()
        
        # Test 3: Simulation de scans
        print("📝 Simulation de scans de test...")
        if self.simulate_scan_log():
            print("✅ Simulation terminée")
        print()
        
        # Test 4: Vérification après simulation
        print("📋 Vérification après simulation:")
        self.check_audit_logs()
        print()
        
        print("🏁 TESTS TERMINÉS")
        print("=" * 50)
        print()
        print("🎯 Pour voir les logs dans l'admin:")
        print("   1. Aller dans: http://127.0.0.1:8000/admin/")
        print("   2. Section 'Audit' → 'Audit logs'")
        print("   3. Filtrer par 'Action = SCAN'")
        print()
        print("🎯 Pour tester avec le scanner réel:")
        print("   1. Démarrer: python simple_scanner/scanner_manual.py")
        print("   2. Scanner des tickets")
        print("   3. Vérifier les logs dans l'admin")

def main():
    """Fonction principale"""
    tester = AuditScannerTester()
    tester.run_tests()

if __name__ == "__main__":
    main()
