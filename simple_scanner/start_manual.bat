@echo off
echo ====================================================================
echo   SCANNER GESTSPORT - VERSION MANUELLE
echo ====================================================================
echo.

echo [1/2] Verification de l'environnement...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python n'est pas installe
    pause
    exit /b 1
)

echo ✅ Python trouve

echo [2/2] Demarrage du scanner manuel...
echo.
echo 🎯 Lancement du scanner GestSport (saisie manuelle prioritaire)...
echo.
echo Instructions:
echo   1. Entrez le numero du ticket dans le champ
echo   2. Appuyez sur ENTREE ou cliquez sur VALIDER
echo   3. Le resultat s'affiche instantanement
echo   4. Le champ se vide automatiquement pour le prochain scan
echo.

python scanner_manual.py

echo.
echo ====================================================================
echo Scanner manuel arrete
echo ====================================================================
pause
