#!/usr/bin/env python3
# ==============================================================================
# FORCER LA MODIFICATION DIRECTE DU FICHIER VIEWS
# ==============================================================================

import os
import re

def force_fix_scanner_logic():
    """Modifie directement le fichier pour forcer la correction"""
    
    file_path = "e:/backend/config/views.py"
    
    # Lire le fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("🔍 Recherche de l'ancienne logique...")
    
    # Vérifier si l'ancienne logique existe encore
    old_pattern = r'if reservation\.start_time > now:'
    if re.search(old_pattern, content):
        print("❌ Ancienne logique détectée - Application du correctif")
        
        # Remplacer l'ancienne logique
        new_logic = """if reservation.start_time > now + timezone.timedelta(hours=2):"""
        content = re.sub(old_pattern, new_logic, content)
        
        # Remplacer aussi le message d'erreur
        old_message = r'"Réservation future"'
        new_message = '"Réservation trop future (plus de 2h)"'
        content = re.sub(old_message, new_message, content)
        
        # Écrire le fichier modifié
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Correction appliquée avec succès")
        return True
    else:
        print("✅ La logique semble déjà corrigée")
        return False

def check_current_logic():
    """Vérifie la logique actuelle dans le fichier"""
    
    file_path = "e:/backend/config/views.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("\n🔍 Vérification des lignes autour de la logique scanner...")
    
    for i, line in enumerate(lines):
        if 'reservation.start_time > now' in line:
            print(f"Ligne {i+1}: {line.strip()}")
            # Afficher les lignes autour
            for j in range(max(0, i-2), min(len(lines), i+5)):
                if j != i:
                    print(f"  {j+1}: {lines[j].rstrip()}")
            break

if __name__ == "__main__":
    print("=" * 60)
    print("   FORCAGE DE LA CORRECTION SCANNER")
    print("=" * 60)
    
    check_current_logic()
    
    if force_fix_scanner_logic():
        print("\n🔄 Le fichier a été modifié.")
        print("📋 Actions requises:")
        print("   1. Arrêtez le serveur Django (Ctrl + C)")
        print("   2. Redémarrez: python manage.py runserver")
        print("   3. Testez avec: TKT-E6D9F077")
    else:
        print("\n✅ La correction est déjà en place.")
        print("📋 Le problème vient du cache de Django.")
        print("   1. Arrêtez TOTALEMENT le serveur")
        print("   2. Fermez le terminal")
        print("   3. Ouvrez un NOUVEAU terminal")
        print("   4. Redémarrez: python manage.py runserver")
