# ==============================================================================
# EXEMPLE DE CONFIGURATION POUR LE SCANNER GESTSPORT
# ==============================================================================
# Copiez ce fichier vers config.py et modifiez les paramètres

# --- CONNEXION API ---
API_BASE_URL = "http://127.0.0.1:8000"  # URL de votre API GestSport
API_TOKEN = "VOTRE_TOKEN_API_ICI"           # Token généré par votre admin Django
SCANNER_ID = "scanner_principal_01"           # Identifiant unique de ce scanner
LOCATION = "Entrée Principale"                # Localisation du scanner

# --- CONNEXION BASE DE DONNÉES POSTGRESQL ---
DB_HOST = "localhost"                      # Host du serveur PostgreSQL
DB_PORT = 5432                            # Port du serveur PostgreSQL
DB_NAME = "gestsport_db"                   # Nom de votre base de données
DB_USER = "scan_user"                       # Utilisateur dédié pour les scanners
DB_PASSWORD = "votre_mot_de_passe_robuste"   # Mot de passe de l'utilisateur scanner
DB_SSL_MODE = "require"                     # Mode SSL (prefer, require, disable)

# --- PARAMÈTRES DE SCAN ---
SCAN_TIMEOUT = 10                           # Timeout en secondes pour les requêtes API
MAX_RETRY_ATTEMPTS = 3                       # Nombre de tentatives de connexion API
RETRY_DELAY = 1000                          # Délai entre tentatives (millisecondes)

# --- OPTIONS INTERFACE ---
ENABLE_SOUNDS = True                        # Activer les sons de feedback
ENABLE_VIBRATION = True                     # Activer la vibration (si supporté)
ENABLE_CAMERA_AUTOFOCUS = True               # Autofocus caméra automatique
CAMERA_RESOLUTION = (1280, 720)            # Résolution caméra (largeur, hauteur)
CAMERA_FPS = 30                            # Images par seconde

# --- LOGGING ---
LOG_FILE = "logs/scanner.log"               # Fichier de log
LOG_LEVEL = "INFO"                         # Niveau de log (DEBUG, INFO, WARNING, ERROR)
MAX_LOG_SIZE_MB = 100                      # Taille maximale du fichier de log (MB)

# --- MODE DÉGRADÉ ---
ENABLE_OFFLINE_MODE = True                  # Activer le mode hors ligne
OFFLINE_QUEUE_FILE = "logs/offline_queue.json"  # File d'attente hors ligne
SYNC_INTERVAL = 60                          # Intervalle de synchronisation (secondes)

# --- SÉCURITÉ ---
ENABLE_ENCRYPTION = True                   # Chiffrer les tokens sensibles
SESSION_TIMEOUT = 3600                      # Timeout de session (secondes)
MAX_FAILED_ATTEMPTS = 5                    # Nombre max d'échecs avant blocage

# --- PERFORMANCE ---
CACHE_DURATION = 300                        # Durée du cache local (secondes)
MAX_CONCURRENT_SCANS = 10                 # Nombre max de scans simultanés
CLEANUP_INTERVAL = 3600                    # Intervalle de nettoyage (secondes)

# --- EXPORT ET RAPPORTS ---
EXPORT_FORMAT = "csv"                       # Format d'export (csv, json, excel)
AUTO_EXPORT_INTERVAL = 86400                # Export automatique (secondes = 24h)
MAX_EXPORT_RECORDS = 10000                 # Nombre max d'enregistrements par export

# --- DÉVELOPPEMENT ---
DEBUG_MODE = False                          # Activer le mode debug
SHOW_CAMERA_PREVIEW = True                   # Afficher la preview caméra
ENABLE_MOCK_SCANS = False                  # Activer les faux scans pour tests

# ==============================================================================
# INSTRUCTIONS DE CONFIGURATION
# ==============================================================================
#
# 1. Copiez ce fichier vers config.py:
#    cp config.example.py config.py
#
# 2. Modifiez les paramètres suivants:
#    - API_BASE_URL: Mettez l'URL de votre API GestSport
#    - API_TOKEN: Mettez le token généré par votre admin Django
#    - DB_HOST: Mettez le host de votre base PostgreSQL
#    - DB_NAME: Mettez le nom de votre base
#    - DB_USER: Créez un utilisateur scan_user dans PostgreSQL
#    - DB_PASSWORD: Mettez un mot de passe robuste
#
# 3. Créez l'utilisateur PostgreSQL:
#    CREATE USER scan_user WITH PASSWORD 'votre_mot_de_passe_robuste';
#    GRANT CONNECT ON DATABASE gestsport_db TO scan_user;
#    GRANT SELECT ON ALL TABLES IN SCHEMA public TO scan_user;
#    GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO scan_user;
#
# 4. Générez un token API dans votre admin Django:
#    - Allez dans /admin/
#    - Section "Tokens" 
#    - Créez un token pour votre scanner
#
# ==============================================================================
