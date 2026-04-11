@echo off
echo ====================================================================
echo   DÉMARRAGE SCANNER GESTSPORT - VERSION STABLE
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

echo [2/2] Demarrage du scanner stable...
echo.
echo 🎯 Lancement du scanner GestSport (version stable sans threading)...
echo.

python scanner_stable.py

echo.
echo ====================================================================
echo Scanner arrete
echo ====================================================================
pause
