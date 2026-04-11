# 📁 Scripts GestSport

Ce dossier contient tous les scripts utilitaires pour la maintenance, le debug et la gestion de GestSport.

## 📂 Structure des dossiers

### 🛠️ `maintenance/`
Scripts de maintenance et nettoyage :
- `clean_and_test_stripe.py` - Nettoyage des données Stripe
- `clean_duplicate_payments.py` - Suppression des paiements en double
- `clear_cache.py` - Vidage du cache système
- `migrate_tickets.py` - Migration des tickets

### 👥 `creation/`
Scripts de création de données de test :
- `create_admin.py` - Création d'un utilisateur admin
- `create_test_users.py` - Création d'utilisateurs de test
- `create_test_reservation.py` - Création de réservations de test

### 🔍 `debug/`
Scripts de debug et diagnostic :
- `debug_payment.py` - Debug des problèmes de paiement
- `debug_stripe_complete.py` - Debug complet de Stripe
- `debug_ticket.py` - Debug des problèmes de tickets

### 💳 `payments/`
Scripts liés aux paiements :
- `check_payment_status.py` - Vérification des statuts de paiement
- `manual_payment_update.py` - Mise à jour manuelle des paiements
- `fix_stripe_config.py` - Correction de la configuration Stripe

### 🎫 `tickets/`
Scripts de gestion des tickets :
- `generate_qr.py` - Génération de codes QR
- `create_test_ticket.py` - Création de tickets de test

## 🚀 Comment utiliser

```bash
# Exécuter un script de maintenance
python scripts/maintenance/clear_cache.py

# Créer des utilisateurs de test
python scripts/creation/create_test_users.py

# Debuguer un problème de paiement
python scripts/payments/debug_payment.py
```

## ⚠️ Important

- Ces scripts sont destinés au développement et à la maintenance
- Toujours faire une sauvegarde avant d'exécuter un script de maintenance
- Les scripts de création sont à utiliser uniquement en environnement de test
