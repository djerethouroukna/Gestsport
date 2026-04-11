@echo off
echo ====================================================================
echo   DÉMARRAGE RAPIDE DU SCANNER GESTSPORT
echo ====================================================================
echo.

echo [1/3] Verification de l'API...
python test_scanner.py
if errorlevel 1 (
    echo.
    echo ⚠️ L'API n'est pas accessible
    echo Assurez-vous que votre serveur Django est démarré:
    echo   cd e:/backend
    echo   python manage.py runserver
    echo.
    echo Le scanner fonctionnera en mode hors ligne.
    echo.
)

echo [2/3] Démarrage du scanner...
echo.
echo 🎯 Lancement du scanner GestSport...
echo.

python scanner_simple.py

echo.
echo ====================================================================
echo Scanner arrêté
echo ====================================================================
pause
