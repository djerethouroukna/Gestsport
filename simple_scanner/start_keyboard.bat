@echo off
echo ====================================================================
echo   SCANNER GESTSPORT - VERSION CLAVIER UNIQUEMENT
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

echo [2/2] Demarrage du scanner clavier...
echo.
echo 🎯 Lancement du scanner GestSport (clavier uniquement)...
echo.
echo Instructions:
echo   1. Tapez directement le numero du ticket au clavier
echo   2. Appuyez sur ENTREE pour valider
echo   3. Le resultat s'affiche instantanement
echo   4. Le champ se vide automatiquement
echo   5. ESC ou DELETE pour effacer
echo.

python scanner_keyboard.py

echo.
echo ====================================================================
echo Scanner clavier arrete
echo ====================================================================
pause
