@echo off
echo ====================================================================
echo   CORRECTION DES PERMISSIONS POUR LE SCANNER
echo ====================================================================
echo.

echo [1/3] Création de l'utilisateur scan_user dans PostgreSQL...
cd ..
python setup_scan_user.py
if errorlevel 1 (
    echo.
    echo ❌ Erreur création utilisateur scan_user
    echo.
    echo Alternative manuelle:
    echo   1. Ouvrez pgAdmin ou psql
    echo   2. Connectez-vous en tant que postgres
    echo   3. Exécutez: CREATE USER scan_user WITH PASSWORD 'INNOCENT';
    echo   4. Exécutez: GRANT CONNECT ON DATABASE gestsport TO scan_user;
    echo   5. Exécutez: GRANT SELECT ON ALL TABLES IN SCHEMA public TO scan_user;
    echo.
    pause
    exit /b 1
)

echo [2/3] Test de la configuration du scanner...
cd simple_scanner
python test_scanner.py

echo [3/3] Démarrage du scanner...
echo.
echo 🎯 Lancement du scanner avec configuration corrigée...
echo.
python scanner_simple.py

pause
