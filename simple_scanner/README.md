# 🎯 Simple Scanner - Système de Validation de Tickets

Un système de scan simple et efficace pour valider les tickets GestSport via API et base de données PostgreSQL.

## 📋 Fonctionnalités

- ✅ **Scan automatique** par QR code (caméra)
- ✅ **Scan manuel** par saisie clavier
- ✅ **Double validation** : Base locale + API distante
- ✅ **Mode hors ligne** : Fonctionnement sans connexion API
- ✅ **Affichage clair** : ✅ Valide ou ❌ Rejeté
- ✅ **Logging complet** : Traçabilité de toutes les validations
- ✅ **Configuration simple** : Paramètres faciles à configurer

## 🏗️ Architecture

```
simple_scanner/
├── scanner.py              # Application principale (console + GUI)
├── config.py              # Configuration API et base de données
├── database.py            # Connexion PostgreSQL et vérifications
├── requirements.txt        # Dépendances Python
├── README.md             # Documentation complète
└── logs/                 # Dossier pour les logs de scans
```

## 🚀 Installation Rapide

1. **Cloner le projet**
   ```bash
   cd e:/backend/
   mkdir simple_scanner
   cd simple_scanner
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurer la connexion**
   - Éditer `config.py`
   - Mettre vos paramètres API et base de données

4. **Lancer le scanner**
   ```bash
   python scanner.py
   ```

## 📱 Modes d'Utilisation

### Mode Console : Interface texte simple
### Mode GUI : Interface graphique avec caméra intégrée
### Mode API : Pour intégration dans d'autres systèmes

## 🔐 Sécurité

- **Connexion sécurisée** à la base PostgreSQL
- **Token API** chiffré et protégé
- **Validation double** pour éviter les fraudes
- **Logs complets** pour audit et traçabilité

## 📊 Performance

- **Validation < 2 secondes**
- **Mode hors ligne** disponible
- **Support multi-scanners**
- **Monitoring temps réel**

---

**Prêt à transformer n'importe quel ordinateur en scanner professionnel GestSport !** 🎯✨
