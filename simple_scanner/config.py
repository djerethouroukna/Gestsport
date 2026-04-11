# ==============================================================================
# CONFIGURATION DU SCANNER GESTSPORT
# ==============================================================================

# --- CONNEXION API ---
API_BASE_URL = "http://127.0.0.1:8000"
API_TOKEN = "909626cbee38e0891afa57bdf023402ad08b9e67"  # Token du scanner principal (mis à jour)
SCANNER_ID = "scanner_simple_01"
LOCATION = "Entrée Principale"

# --- CONNEXION BASE DE DONNÉES POSTGRESQL ---
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "gestsport"
DB_USER = "scan_user"
DB_PASSWORD = "INNOCENT"  # À modifier avec votre mot de passe
DB_SSL_MODE = "prefer"

# --- PARAMÈTRES DE SCAN ---
SCAN_TIMEOUT = 15  # Timeout en secondes pour les requêtes API (augmenté)
AUDIT_TIMEOUT = 10  # Timeout pour les logs d'audit
MAX_RETRY_ATTEMPTS = 3  # Nombre de tentatives de connexion API
RETRY_DELAY = 1000  # Délai entre tentatives (ms)
CONNECTION_CHECK_TIMEOUT = 3  # Timeout pour vérifier la connexion

# --- OPTIONS INTERFACE ---
ENABLE_SOUNDS = True  # Activer les sons de feedback
ENABLE_VIBRATION = True  # Activer la vibration (si supporté)
ENABLE_CAMERA_AUTOFOCUS = True  # Autofocus caméra automatique
CAMERA_RESOLUTION = (1280, 720)  # Résolution caméra (largeur, hauteur)
CAMERA_FPS = 30  # Images par seconde

# --- LOGGING ---
LOG_FILE = "logs/scans.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
MAX_LOG_SIZE_MB = 100  # Taille maximale du fichier de log (MB)

# --- MODE DÉGRADÉ ---
ENABLE_OFFLINE_MODE = True  # Activer le mode hors ligne
OFFLINE_QUEUE_FILE = "logs/offline_queue.json"
SYNC_INTERVAL = 60  # Intervalle de synchronisation (secondes)

# --- SÉCURITÉ ---
ENABLE_ENCRYPTION = True  # Chiffrer les tokens sensibles
SESSION_TIMEOUT = 3600  # Timeout de session (secondes)
MAX_FAILED_ATTEMPTS = 5  # Nombre max d'échecs avant blocage

# --- PERFORMANCE ---
CACHE_DURATION = 300  # Durée du cache local (secondes)
MAX_CONCURRENT_SCANS = 10  # Nombre max de scans simultanés
CLEANUP_INTERVAL = 3600  # Intervalle de nettoyage (secondes)

# --- EXPORT ET RAPPORTS ---
EXPORT_FORMAT = "csv"  # csv, json, excel
AUTO_EXPORT_INTERVAL = 86400  # Export automatique (secondes = 24h)
MAX_EXPORT_RECORDS = 10000  # Nombre max d'enregistrements par export

# --- DÉVELOPPEMENT ---
DEBUG_MODE = False  # Activer le mode debug
SHOW_CAMERA_PREVIEW = True  # Afficher la preview caméra
ENABLE_MOCK_SCANS = False  # Activer les faux scans pour tests

# ==============================================================================
# FONCTIONS DE CONFIGURATION
# ==============================================================================

def get_api_config():
    """Retourne la configuration API"""
    return {
        'base_url': API_BASE_URL,
        'token': API_TOKEN,
        'scanner_id': SCANNER_ID,
        'location': LOCATION,
        'timeout': SCAN_TIMEOUT
    }

def get_database_config():
    """Retourne la configuration base de données"""
    return {
        'host': DB_HOST,
        'port': DB_PORT,
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD,
        'sslmode': DB_SSL_MODE
    }

def get_camera_config():
    """Retourne la configuration caméra"""
    return {
        'resolution': CAMERA_RESOLUTION,
        'fps': CAMERA_FPS,
        'autofocus': ENABLE_CAMERA_AUTOFOCUS
    }

def get_logging_config():
    """Retourne la configuration logging"""
    return {
        'file': LOG_FILE,
        'level': LOG_LEVEL,
        'max_size_mb': MAX_LOG_SIZE_MB
    }

def is_offline_mode_enabled():
    """Vérifie si le mode hors ligne est activé"""
    return ENABLE_OFFLINE_MODE

def get_retry_config():
    """Retourne la configuration des tentatives"""
    return {
        'max_attempts': MAX_RETRY_ATTEMPTS,
        'delay': RETRY_DELAY
    }

# ==============================================================================
# VALIDATION DE CONFIGURATION
# ==============================================================================

def validate_config():
    """Valide la configuration et retourne les erreurs"""
    errors = []
    
    # Vérifier les paramètres obligatoires
    if not API_BASE_URL:
        errors.append("API_BASE_URL est obligatoire")
    if not API_TOKEN:
        errors.append("API_TOKEN est obligatoire")
    if not DB_HOST:
        errors.append("DB_HOST est obligatoire")
    if not DB_NAME:
        errors.append("DB_NAME est obligatoire")
    if not DB_USER:
        errors.append("DB_USER est obligatoire")
    
    # Vérifier les formats
    if DB_PORT and (not isinstance(DB_PORT, int) or DB_PORT < 1 or DB_PORT > 65535):
        errors.append("DB_PORT doit être un entier entre 1 et 65535")
    
    if SCAN_TIMEOUT and (not isinstance(SCAN_TIMEOUT, (int, float)) or SCAN_TIMEOUT <= 0):
        errors.append("SCAN_TIMEOUT doit être un nombre positif")
    
    return errors

if __name__ == "__main__":
    # Validation au démarrage
    config_errors = validate_config()
    if config_errors:
        print("❌ Erreurs de configuration:")
        for error in config_errors:
            print(f"  - {error}")
        exit(1)
    else:
        print("✅ Configuration valide")
        print(f"🎫 Scanner ID: {SCANNER_ID}")
        print(f"🌐 API URL: {API_BASE_URL}")
        print(f"🗄️ Base: {DB_NAME}@{DB_HOST}:{DB_PORT}")
