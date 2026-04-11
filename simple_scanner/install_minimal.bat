@echo off
echo ====================================================================
echo   INSTALLATION MINIMALE SCANNER GESTSPORT
echo ====================================================================
echo.

echo [1/4] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python n'est pas installe
    echo Veuillez installer Python 3.8+ depuis https://python.org
    pause
    exit /b 1
)

echo ✅ Python trouve

echo [2/4] Installation des dependances essentielles...
echo Installation de psycopg2-binary...
python -m pip install psycopg2-binary
echo Installation de requests...
python -m pip install requests
echo Installation de opencv-python...
python -m pip install opencv-python
echo Installation de Pillow...
python -m pip install Pillow
echo Installation de pyzbar...
python -m pip install pyzbar

echo ✅ Dependances essentielles installees

echo [3/4] Creation des dossiers...
if not exist logs mkdir logs
if not exist data mkdir data

echo ✅ Dossiers crees

echo [4/4] Creation du fichier de configuration...
if not exist config.py (
    echo Creation de config.py avec valeurs par defaut...
    (
        echo # Configuration minimale pour le scanner GestSport
        echo API_BASE_URL = "http://127.0.0.1:8000"
        echo API_TOKEN = "a9dc052f48d8098984e2f916673b51ed2e364929"
        echo SCANNER_ID = "scanner_minimal_01"
        echo LOCATION = "Entrée Principale"
        echo.
        echo DB_HOST = "localhost"
        echo DB_PORT = 5432
        echo DB_NAME = "gestsport_db"
        echo DB_USER = "scan_user"
        echo DB_PASSWORD = "password"
        echo DB_SSL_MODE = "require"
        echo.
        echo SCAN_TIMEOUT = 10
        echo MAX_RETRY_ATTEMPTS = 3
        echo RETRY_DELAY = 1000
        echo.
        echo LOG_FILE = "logs/scanner.log"
        echo LOG_LEVEL = "INFO"
        echo MAX_LOG_SIZE_MB = 100
        echo.
        echo ENABLE_OFFLINE_MODE = True
        echo OFFLINE_QUEUE_FILE = "logs/offline_queue.json"
        echo SYNC_INTERVAL = 60
    ) > config.py
    echo ✅ Fichier config.py cree
) else (
    echo ✅ Configuration existante trouvee
)

echo.
echo ====================================================================
echo 🎯 INSTALLATION TERMINÉE !
echo ====================================================================
echo.
echo Fichier de configuration: config.py
echo Logs: logs/scanner.log
echo.
echo MODIFIEZ config.py AVEC VOS PARAMÈTRES AVANT DE LANCER:
echo   - API_BASE_URL: URL de votre API GestSport
echo   - API_TOKEN: Token d'authentification
echo   - DB_HOST, DB_NAME, DB_USER, DB_PASSWORD: Base de donnees
echo.
echo Pour demarrer le scanner:
echo   python scanner.py
echo.
pause
