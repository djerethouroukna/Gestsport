#!/usr/bin/env python3
"""
Script pour remplacer tous les symboles € par FCFA dans les templates
"""

import os
import re

def replace_euro_in_templates():
    """Remplacer tous les € par FCFA dans les fichiers templates"""
    
    templates_dir = "e:/backend/templates"
    replacements_made = 0
    files_processed = 0
    
    # Parcourir tous les fichiers HTML
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                
                try:
                    # Lire le fichier
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Remplacer les symboles €
                    original_content = content
                    
                    # Remplacer € par FCFA
                    content = re.sub(r'FCFA', ' FCFA', content)
                    
                    # Compter les remplacements
                    if content != original_content:
                        euro_count = original_content.count('FCFA')
                        replacements_made += euro_count
                        
                        # Écrire le fichier modifié
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        print(f"OK {file_path}: {euro_count} remplacements")
                        files_processed += 1
                
                except Exception as e:
                    print(f"ERREUR avec {file_path}: {e}")
    
    print(f"\n=== RESUME ===")
    print(f"Fichiers modifiés: {files_processed}")
    print(f"Total remplacements: {replacements_made}")
    print("Tous les symboles € ont été remplacés par FCFA")

if __name__ == "__main__":
    replace_euro_in_templates()
