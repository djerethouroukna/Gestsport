#!/usr/bin/env python
"""
Script pour tester les dépendances localement avant déploiement
"""
import subprocess
import sys
import os

def test_requirements_file(filename):
    """Teste un fichier requirements"""
    print(f"\n=== Test de {filename} ===")
    
    try:
        # Créer un environnement virtuel temporaire
        venv_dir = f"test_env_{filename.replace('.txt', '')}"
        
        # Créer l'environnement virtuel
        print(f"Création de l'environnement virtuel {venv_dir}...")
        result = subprocess.run([
            sys.executable, "-m", "venv", venv_dir
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Erreur création venv: {result.stderr}")
            return False
        
        # Activer l'environnement et installer les packages
        if os.name == 'nt':  # Windows
            pip_path = f"{venv_dir}\\Scripts\\pip"
        else:  # Unix
            pip_path = f"{venv_dir}/bin/pip"
        
        print(f"Installation des packages depuis {filename}...")
        result = subprocess.run([
            pip_path, "install", "-r", filename
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"SUCCESS: {filename} installé correctement")
            print(f"Packages installés: {len(result.stdout.split('Successfully installed'))}")
            return True
        else:
            print(f"ERREUR: {filename} - {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Erreur test {filename}: {e}")
        return False

def main():
    """Teste tous les fichiers requirements"""
    requirements_files = [
        "requirements.txt",
        "requirements-minimal.txt",
        "requirements-mobile.txt"
    ]
    
    results = {}
    
    for req_file in requirements_files:
        if os.path.exists(req_file):
            results[req_file] = test_requirements_file(req_file)
        else:
            print(f"Fichier {req_file} non trouvé")
            results[req_file] = False
    
    print("\n=== RÉSULTATS ===")
    for filename, success in results.items():
        status = "SUCCESS" if success else "ERREUR"
        print(f"{filename}: {status}")
    
    # Nettoyer les environnements virtuels
    print("\nNettoyage des environnements virtuels...")
    for req_file in requirements_files:
        venv_dir = f"test_env_{req_file.replace('.txt', '')}"
        if os.path.exists(venv_dir):
            try:
                import shutil
                shutil.rmtree(venv_dir)
                print(f"Nettoyé: {venv_dir}")
            except:
                print(f"Impossible de nettoyer: {venv_dir}")

if __name__ == "__main__":
    main()
