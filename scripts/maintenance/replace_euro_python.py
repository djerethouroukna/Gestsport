#!/usr/bin/env python3
"""
Script pour remplacer FCFA/FCFA/FCFA par FCFA dans les fichiers Python
"""

import os
import re

def replace_euro_in_python():
    """Remplacer FCFA/FCFA/FCFA par FCFA dans les fichiers Python"""
    
    backend_dir = "e:/backend"
    replacements_made = 0
    files_processed = 0
    
    # Patterns à remplacer
    patterns = [
        (r'\beuro\b', 'FCFA'),
        (r'\bEuro\b', 'FCFA'),
        (r'\bEUR\b', 'FCFA'),
        (r'"FCFA"', '"FCFA"'),
        (r"'FCFA'", "'FCFA'"),
    ]
    
    # Parcourir tous les fichiers Python
    for root, dirs, files in os.walk(backend_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                try:
                    # Ignorer les fichiers de migration
                    if 'migrations' in root:
                        continue
                    
                    # Lire le fichier
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Remplacer les patterns
                    original_content = content
                    total_replacements = 0
                    
                    for pattern, replacement in patterns:
                        old_content = content
                        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                        replacements_in_pattern = len(re.findall(pattern, old_content, flags=re.IGNORECASE))
                        total_replacements += replacements_in_pattern
                    
                    # Compter les remplacements
                    if content != original_content:
                        replacements_made += total_replacements
                        
                        # Écrire le fichier modifié
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        print(f"OK {file_path}: {total_replacements} remplacements")
                        files_processed += 1
                
                except Exception as e:
                    print(f"ERREUR avec {file_path}: {e}")
    
    print(f"\n=== RESUME ===")
    print(f"Fichiers modifiés: {files_processed}")
    print(f"Total remplacements: {replacements_made}")
    print("Tous les FCFA/FCFA/FCFA ont été remplacés par FCFA")

if __name__ == "__main__":
    replace_euro_in_python()
