#!/usr/bin/env python
"""
Script pour vérifier où Pillow est utilisé dans le code
"""
import os
import re

def find_pillow_usage():
    """Trouve toutes les utilisations de Pillow dans le code"""
    
    pillow_imports = [
        r'from PIL import',
        r'import PIL',
        r'from Pillow import',
        r'import Pillow',
        r'Image\.open',
        r'Image\.new',
        r'ImageDraw\.Draw',
    ]
    
    pillow_files = {}
    
    # Parcourir tous les fichiers Python
    for root, dirs, files in os.walk('.'):
        # Ignorer les dossiers venv et __pycache__
        if 'venv' in root or '__pycache__' in root or '.git' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Vérifier les imports Pillow
                    for pattern in pillow_imports:
                        if re.search(pattern, content):
                            if file_path not in pillow_files:
                                pillow_files[file_path] = []
                            pillow_files[file_path].append(pattern)
                            
                except Exception as e:
                    print(f"Erreur lecture {file_path}: {e}")
    
    return pillow_files

def main():
    """Affiche les utilisations de Pillow"""
    print("=== Recherche d'utilisation de Pillow ===\n")
    
    pillow_usage = find_pillow_usage()
    
    if not pillow_usage:
        print("Aucune utilisation de Pillow trouvée !")
        print("Le déploiement devrait fonctionner sans Pillow.")
    else:
        print(f"Utilisations de Pillow trouvées dans {len(pillow_usage)} fichiers :\n")
        
        for file_path, patterns in pillow_usage.items():
            print(f"Fichier : {file_path}")
            for pattern in patterns:
                print(f"  - {pattern}")
            print()
        
        print("\n=== Solutions possibles ===")
        print("1. Commenter/désactiver temporairement ces fonctionnalités")
        print("2. Utiliser des alternatives (ex: stockage d'URLs au lieu d'images)")
        print("3. Créer des conditions pour désactiver ces features sur Render")
        
        print("\n=== Commandes pour désactiver temporairement ===")
        for file_path in pillow_usage.keys():
            print(f"# Pour désactiver dans {file_path}:")
            print(f"# Ajouter 'if not getattr(settings, \"PILLOW_ENABLED\", True):' au début")

if __name__ == "__main__":
    main()
