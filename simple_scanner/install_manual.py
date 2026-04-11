#!/usr/bin/env python3
# ==============================================================================
# INSTALLATION MANUELLE DES DÉPENDANCES
# ==============================================================================

import subprocess
import sys
import os

def run_command(command, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n📦 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} réussie")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur {description}: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Vérifie la version de Python"""
    print("🐍 Vérification de Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} trouvé")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} trop ancien")
        print("Veuillez installer Python 3.8+")
        return False

def install_dependencies():
    """Installe les dépendances une par une"""
    dependencies = [
        ("psycopg2-binary", "Base de données PostgreSQL"),
        ("requests", "Client HTTP pour l'API"),
        ("opencv-python", "Traitement d'images"),
        ("Pillow", "Manipulation d'images"),
        ("pyzbar", "Détection QR codes"),
        ("python-dateutil", "Utilitaires de date"),
        ("cryptography", "Sécurité"),
        ("psutil", "Monitoring système")
    ]
    
    failed = []
    
    for package, description in dependencies:
        if not run_command(f"pip install {package}", f"Installation de {description}"):
            failed.append(package)
    
    return failed

def test_imports():
    """Teste l'importation des modules"""
    print("\n🧪 Test des imports...")
    
    test_modules = [
        ("psycopg2", "psycopg2-binary"),
        ("requests", "requests"),
        ("cv2", "opencv-python"),
        ("PIL", "Pillow"),
        ("pyzbar", "pyzbar"),
        ("dateutil", "python-dateutil"),
        ("cryptography", "cryptography"),
        ("psutil", "psutil")
    ]
    
    failed_imports = []
    
    for module_name, package_name in test_modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name} importé avec succès")
        except ImportError as e:
            print(f"❌ Erreur import {module_name}: {e}")
            failed_imports.append(package_name)
    
    return failed_imports

def create_directories():
    """Crée les dossiers nécessaires"""
    print("\n📁 Création des dossiers...")
    
    directories = ["logs", "data"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Dossier {directory} créé")
        else:
            print(f"✅ Dossier {directory} existe déjà")

def create_config_if_missing():
    """Crée le fichier de configuration s'il manque"""
    print("\n⚙️ Vérification de la configuration...")
    
    if not os.path.exists("config.py"):
        print("📝 Création du fichier config.py...")
        
        config_content = '''# Configuration minimale pour le scanner GestSport
API_BASE_URL = "http://127.0.0.1:8000"
API_TOKEN = "a9dc052f48d8098984e2f916673b51ed2e364929"
SCANNER_ID = "scanner_manual_01"
LOCATION = "Entrée Principale"

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "gestsport_db"
DB_USER = "scan_user"
DB_PASSWORD = "password"
DB_SSL_MODE = "require"

SCAN_TIMEOUT = 10
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1000

LOG_FILE = "logs/scanner.log"
LOG_LEVEL = "INFO"
MAX_LOG_SIZE_MB = 100

ENABLE_OFFLINE_MODE = True
OFFLINE_QUEUE_FILE = "logs/offline_queue.json"
SYNC_INTERVAL = 60
'''
        
        with open("config.py", "w") as f:
            f.write(config_content)
        
        print("✅ Fichier config.py créé")
        print("⚠️ MODIFIEZ LES PARAMÈTRES DANS config.py AVANT D'UTILISER")
    else:
        print("✅ Fichier config.py existe déjà")

def main():
    """Fonction principale d'installation"""
    print("=" * 60)
    print("   INSTALLATION MANUELLE SCANNER GESTSPORT")
    print("=" * 60)
    
    # Vérification Python
    if not check_python_version():
        input("Appuyez sur Entrée pour quitter...")
        return
    
    # Mise à jour pip
    run_command("python -m pip install --upgrade pip", "Mise à jour de pip")
    
    # Installation des dépendances
    print("\n📦 Installation des dépendances...")
    failed_packages = install_dependencies()
    
    if failed_packages:
        print(f"\n⚠️ Packages échoués: {', '.join(failed_packages)}")
        print("Tentative d'installation avec versions alternatives...")
        
        for package in failed_packages:
            if package == "opencv-python":
                run_command("pip install opencv-python==4.8.0.76", "Installation opencv-python version spécifique")
            elif package == "pyzbar":
                run_command("pip install pyzbar==0.1.9", "Installation pyzbar version spécifique")
    
    # Test des imports
    failed_imports = test_imports()
    
    if failed_imports:
        print(f"\n❌ Imports échoués: {', '.join(failed_imports)}")
        print("L'installation a échoué")
        input("Appuyez sur Entrée pour quitter...")
        return
    
    # Création des dossiers
    create_directories()
    
    # Création de la configuration
    create_config_if_missing()
    
    # Test final
    print("\n🧪 Test final de l'application...")
    try:
        from config import get_api_config
        from database import test_connexion_base
        
        api_config = get_api_config()
        print(f"✅ Configuration API: {api_config['base_url']}")
        
        print("\n🎯 INSTALLATION TERMINÉE AVEC SUCCÈS !")
        print("=" * 60)
        print("Pour démarrer le scanner:")
        print("  python scanner.py")
        print("\nPour tester la configuration:")
        print("  python config.py")
        print("\nPour tester la base de données:")
        print("  python database.py")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erreur test final: {e}")
        print("L'installation a échoué")
    
    input("\nAppuyez sur Entrée pour continuer...")

if __name__ == "__main__":
    main()
