@echo off
echo ====================================================================
echo   INSTALLATION SCANNER GESTSPORT
echo ====================================================================
echo.

echo [1/5] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python n'est pas installe
    echo Veuillez installer Python 3.8+ depuis https://python.org
    pause
    exit /b 1
)

echo ✅ Python trouve

echo [2/5] Installation des dependances...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Erreur installation des dependances
    pause
    exit /b 1
)

echo ✅ Dependances installees

echo [3/5] Creation des dossiers...
if not exist logs mkdir logs
if not exist data mkdir data

echo ✅ Dossiers crees

echo [4/5] Configuration...
if not exist config.py (
    echo.
    echo ⚠️ Fichier config.py non trouve
    echo Veuillez copier config.example.py vers config.py
    echo Et modifier les parametres suivants:
    echo   - API_BASE_URL: URL de votre API GestSport
    echo   - API_TOKEN: Token d'authentification
    echo   - DB_HOST: Host de votre base PostgreSQL
    echo   - DB_NAME: Nom de la base de donnees
    echo   - DB_USER: Utilisateur de la base
    echo   - DB_PASSWORD: Mot de passe de la base
    pause
    exit /b 1
)

echo ✅ Configuration trouvee

echo [5/5] Demarrage du scanner...
echo.
echo 🎯 Scanner GestSport est pret !
echo.
python scanner.py

pause
