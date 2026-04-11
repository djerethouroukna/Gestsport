#!/usr/bin/env python
"""
Script de test pour le système d'audit
"""

import os
import sys
import django

# Configuration de l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from reservations.models import Reservation
from audit.models import AuditLog
from terrains.models import Terrain

User = get_user_model()

def test_audit_system():
    """Test complet du système d'audit"""
    print("🧪 Test du système d'audit")
    print("=" * 50)
    
    # 1. Vérifier que le modèle AuditLog fonctionne
    try:
        total_logs = AuditLog.objects.count()
        print(f"✅ Modèle AuditLog fonctionnel - {total_logs} logs existants")
    except Exception as e:
        print(f"❌ Erreur modèle AuditLog: {e}")
        return
    
    # 2. Créer un utilisateur de test
    try:
        test_user, created = User.objects.get_or_create(
            email='audit_test@example.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Audit',
                'role': 'player'
            }
        )
        if created:
            test_user.set_password('test123')
            test_user.save()
            print("✅ Utilisateur de test créé")
        else:
            print("✅ Utilisateur de test existant")
    except Exception as e:
        print(f"❌ Erreur création utilisateur: {e}")
        return
    
    # 3. Créer une réservation de test
    try:
        terrain = Terrain.objects.first()
        if not terrain:
            print("❌ Aucun terrain trouvé - création impossible")
            return
            
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        reservation = Reservation.objects.create(
            user=test_user,
            terrain=terrain,
            start_time=timezone.now() + timedelta(hours=2),
            end_time=timezone.now() + timedelta(hours=3),
            status='pending'
        )
        print(f"✅ Réservation de test créée (ID: {reservation.id})")
    except Exception as e:
        print(f"❌ Erreur création réservation: {e}")
        return
    
    # 4. Vérifier les logs générés
    try:
        logs_after = AuditLog.objects.count()
        new_logs = logs_after - total_logs
        
        print(f"📊 Nombre de nouveaux logs: {new_logs}")
        
        # Afficher les logs récents
        recent_logs = AuditLog.objects.order_by('-timestamp')[:5]
        print("\n📋 Logs récents:")
        for log in recent_logs:
            user_str = log.user.email if log.user else "Système"
            print(f"  - {log.timestamp.strftime('%H:%M:%S')} | {user_str} | {log.action} | {log.model_name}")
            
    except Exception as e:
        print(f"❌ Erreur lecture logs: {e}")
    
    # 5. Tester une modification
    try:
        reservation.status = 'confirmed'
        reservation.save()
        print("✅ Modification de réservation testée")
        
        # Vérifier le log de modification
        update_log = AuditLog.objects.filter(
            action='UPDATE',
            model_name='Reservation',
            object_id=reservation.id
        ).first()
        
        if update_log and update_log.changes:
            print(f"✅ Log de modification capturé: {list(update_log.changes.keys())}")
        else:
            print("⚠️ Log de modification non trouvé ou vide")
            
    except Exception as e:
        print(f"❌ Erreur test modification: {e}")
    
    # 6. Nettoyage
    try:
        reservation.delete()
        print("✅ Réservation de test supprimée")
        
        # Vérifier le log de suppression
        delete_log = AuditLog.objects.filter(
            action='DELETE',
            model_name='Reservation'
        ).first()
        
        if delete_log:
            print("✅ Log de suppression capturé")
        else:
            print("⚠️ Log de suppression non trouvé")
            
    except Exception as e:
        print(f"❌ Erreur nettoyage: {e}")
    
    print("\n🎉 Test du système d'audit terminé!")
    print(f"📈 Total de logs dans le système: {AuditLog.objects.count()}")

if __name__ == '__main__':
    test_audit_system()
