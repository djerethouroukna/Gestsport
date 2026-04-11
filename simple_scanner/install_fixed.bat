@echo off
echo ====================================================================
echo   INSTALLATION SCANNER GESTSPORT - VERSION CORRIGÉE
echo ====================================================================
echo.

echo [1/6] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python n'est pas installe
    echo Veuillez installer Python 3.8+ depuis https://python.org
    pause
    exit /b 1
)

echo ✅ Python trouve

echo [2/6] Mise a jour de pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ⚠️ Erreur mise a jour pip, continuation...
)

echo ✅ Pip mis a jour

echo [3/6] Installation des dependances...
echo Installation de psycopg2-binary...
python -m pip install psycopg2-binary
if errorlevel 1 (
    echo ❌ Erreur installation psycopg2-binary
    pause
    exit /b 1
)

echo Installation de requests...
python -m pip install requests
if errorlevel 1 (
    echo ❌ Erreur installation requests
    pause
    exit /b 1
)

echo Installation de opencv-python...
python -m pip install opencv-python
if errorlevel 1 (
    echo ❌ Erreur installation opencv-python
    echo Tentative avec version specifique...
    python -m pip install opencv-python==4.8.0.76
    if errorlevel 1 (
        echo ❌ Erreur installation opencv-python
        pause
        exit /b 1
    )
)

echo Installation de Pillow...
python -m pip install Pillow
if errorlevel 1 (
    echo ❌ Erreur installation Pillow
    pause
    exit /b 1
)

echo Installation de pyzbar...
python -m pip install pyzbar
if errorlevel 1 (
    echo ❌ Erreur installation pyzbar
    pause
    exit /b 1
)

echo Installation des dependances supplementaires...
python -m pip install python-dateutil cryptography psutil
if errorlevel 1 (
    echo ⚠️ Erreur dependances supplementaires, continuation...
)

echo ✅ Dependances installees

echo [4/6] Creation des dossiers...
if not exist logs mkdir logs
if not exist data mkdir data

echo ✅ Dossiers crees

echo [5/6] Verification de la configuration...
if not exist config.py (
    echo.
    echo ⚠️ Fichier config.py non trouve
    echo Creation du fichier de configuration depuis l'exemple...
    copy config.example.py config.py
    if errorlevel 1 (
        echo ❌ Erreur copie configuration
        pause
        exit /b 1
    )
    echo ✅ Fichier config.py cree
    echo.
    echo ⚠️ MODIFIEZ LES PARAMÈTRES SUIVANTS DANS config.py:
    echo   - API_BASE_URL: URL de votre API GestSport
    echo   - API_TOKEN: Token d'authentification
    echo   - DB_HOST: Host de votre base PostgreSQL
    echo   - DB_NAME: Nom de la base de donnees
    echo   - DB_USER: Utilisateur de la base
    echo   - DB_PASSWORD: Mot de passe de la base
    echo.
    echo Appuyez sur une touche pour continuer...
    pause
) else (
    echo ✅ Configuration trouvee
)

echo [6/6] Test de la configuration...
python -c "import psycopg2, requests, cv2, PIL, pyzbar; print('✅ Tous les modules importes avec succes')"
if errorlevel 1 (
    echo ❌ Erreur import des modules
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo 🎯 SCANNER GESTSPORT EST PRÊT !
echo ====================================================================
echo.
echo Pour demarrer le scanner:
echo   python scanner.py
echo.
echo Pour verifier la configuration:
echo   python config.py
echo.
echo Pour tester la base de donnees:
echo   python database.py
echo.
echo Appuyez sur une touche pour demarrer le scanner...
pause
python scanner.py
