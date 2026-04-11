#!/bin/bash
# ==============================================================================
# SCRIPT D'INSTALLATION POUR LINUX/MAC
# ==============================================================================

echo "===================================================================="
echo "   INSTALLATION SCANNER GESTSPORT"
echo "===================================================================="
echo

# Vérification de Python
echo "[1/5] Vérification de Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    echo "Veuillez installer Python 3.8+ depuis https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python $PYTHON_VERSION trouvé"

# Installation des dépendances
echo "[2/5] Installation des dépendances..."
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Erreur installation des dépendances"
    exit 1
fi
echo "✅ Dépendances installées"

# Création des dossiers
echo "[3/5] Création des dossiers..."
mkdir -p logs
mkdir -p data
echo "✅ Dossiers créés"

# Configuration
echo "[4/5] Vérification de la configuration..."
if [ ! -f "config.py" ]; then
    echo ""
    echo "⚠️ Fichier config.py non trouvé"
    echo "Veuillez copier config.example.py vers config.py"
    echo "Et modifier les paramètres suivants:"
    echo "  - API_BASE_URL: URL de votre API GestSport"
    echo "  - API_TOKEN: Token d'authentification"
    echo "  - DB_HOST: Host de votre base PostgreSQL"
    echo "  - DB_NAME: Nom de la base de données"
    echo "  - DB_USER: Utilisateur de la base"
    echo "  - DB_PASSWORD: Mot de passe de la base"
    echo ""
    exit 1
fi
echo "✅ Configuration trouvée"

# Test de connexion à la base
echo "[5/5] Test de connexion à la base..."
python3 -c "from database import test_connexion_base; result = test_connexion_base(); print(f'✅ {result[\"message\"]}' if result['success'] else f'❌ {result[\"message\"]}')"

echo ""
echo "===================================================================="
echo "🎯 Scanner GestSport est prêt !"
echo "===================================================================="
echo ""
echo "Pour démarrer le scanner:"
echo "  python3 scanner.py"
echo ""
echo "Ou utilisez le mode console:"
echo "  python3 -c \"from scanner import console_mode; console_mode()\""
echo ""
