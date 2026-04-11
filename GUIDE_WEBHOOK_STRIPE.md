# 📋 GUIDE COMPLET CONFIGURATION WEBHOOK STRIPE

## 🎯 OBJECTIF
Configurer le webhook Stripe pour que les paiements soient automatiquement synchronisés avec votre application GestSport.

---

## 📋 PRÉREQUIS

### ✅ Configuration déjà faite
- **Stripe Secret Key** : ✅ Configuré
- **Stripe Publishable Key** : ✅ Configuré  
- **Webhook Secret** : ✅ Configuré dans settings.py
- **Vue webhook** : ✅ Créée (`/payments/stripe/webhook/`)
- **URL serveur** : ✅ `http://127.0.0.1:8000`

---

## 🌐 ÉTAPE 1 : ACCÈS DASHBOARD STRIPE

1. **Allez sur** : https://dashboard.stripe.com
2. **Connectez-vous** avec vos identifiants Stripe
3. **Vérifiez le mode** : Assurez-vous d'être en **mode TEST** (toggle en haut à gauche)

---

## 🔧 ÉTAPE 2 : CRÉATION WEBHOOK

1. **Menu gauche** → Cliquez sur **"Développeurs"** (Developers)
2. **Sous-menu** → Cliquez sur **"Webhooks"**
3. **Bouton en haut** → Cliquez sur **"Add endpoint"**

---

## 📝 ÉTAPE 3 : CONFIGURATION ENDPOINT

### 📍 Endpoint URL
```
http://127.0.0.1:8000/payments/stripe/webhook/
```

### 🔑 Signing Secret
```
AMadl1WEIkJ1c6DePnBYYa1LIcwvUUUbmCmXPV7d4pk
```

### 📝 Description
```
Webhook GestSport - Paiements automatiques
```

### 📡 HTTP Method
```
POST request
```

---

## 🎯 ÉTAPE 4 : ÉVÉNEMENTS À ÉCOUTER

Cochez ces 3 événements essentiels :

### ✅ checkout.session.completed
- **Quand** : Un client termine le checkout Stripe
- **Action** : Mettre le paiement à "paid"
- **Notification** : Notifier l'admin

### ✅ payment_intent.succeeded  
- **Quand** : Un paiement est réussi
- **Action** : Confirmer le statut
- **Notification** : Backup de notification

### ✅ payment_intent.payment_failed
- **Quand** : Un paiement échoue
- **Action** : Mettre à jour le statut
- **Notification** : Informer de l'échec

---

## ⚙️ ÉTAPE 5 : PARAMÈTRES AVANCÉS

### 📋 Options recommandées
- **API version** : Laissez par défaut
- **Retry mechanism** : Laissez par défaut (3 tentatives)
- **Timeout** : 30 secondes

---

## ✅ ÉTAPE 6 : FINALISATION

1. **Vérifiez** toutes les informations
2. **Cliquez** sur **"Add endpoint"** (en bas)
3. **Confirmez** : L'endpoint apparaît dans la liste
4. **Statut** : Devrait être **"Enabled"** (vert)

---

## 🧪 ÉTAPE 7 : TEST DU WEBHOOK

### 📋 Test depuis Stripe Dashboard
1. **Cliquez sur votre webhook** dans la liste
2. **Onglet "Sending test data"** → Cliquez dessus
3. **Sélectionnez** : `checkout.session.completed`
4. **Cliquez** : **"Send test webhook"**
5. **Vérifiez** : Statut "Succeeded" dans les logs

### 📋 Test local
```bash
# Redémarrez le serveur Django
python manage.py runserver

# Vérifiez les logs du serveur
# Vous devriez voir : "=== STRIPE WEBHOOK REÇU ==="
```

---

## 🔍 ÉTAPE 8 : VÉRIFICATION

### ✅ Vérifiez la configuration
```bash
# Test de configuration
python test_webhook_config.py
```

### ✅ Résultat attendu
```
✅ Stripe Secret Key: Configuré
✅ Stripe Publishable Key: Configuré  
✅ Stripe Webhook Secret: Configuré
✅ Vue stripe_webhook trouvée
```

---

## 🚀 ÉTAPE 9 : TEST COMPLET

### 📋 Créez une réservation de test
1. **Connectez-vous** en coach
2. **Créez une réservation** 
3. **Passez au paiement** Stripe
4. **Utilisez carte test** : `4242 4242 4242 4242`
5. **Validez le paiement**

### 📋 Vérifiez le résultat
1. **Admin** : Devrait recevoir une notification automatique
2. **Base de données** : Payment.status devrait passer à "paid"
3. **Réservation** : is_paid devrait être True
4. **Workflow** : Admin peut confirmer la réservation

---

## 🎯 RÉSULTAT FINAL

### ✅ Après configuration réussie
- **Paiements automatiques** : Plus besoin de mise à jour manuelle
- **Notifications instantanées** : Admin notifié immédiatement  
- **Workflow fluide** : Paiement → Notification → Confirmation → Ticket
- **Fiabilité** : Plus d'erreurs de synchronisation

### ✅ Messages de succès attendus
```
=== STRIPE WEBHOOK REÇU ===
Webhook Stripe reçu: checkout.session.completed
Paiement réussi pour réservation XX
✅ Notifications créées pour 1 admin(s)
```

---

## 🆘 DÉPANNAGE

### ❌ Si webhook ne fonctionne pas
1. **Vérifiez l'URL** : `http://127.0.0.1:8000/payments/stripe/webhook/`
2. **Vérifiez le secret** : Copiez exactement `AMadl1WEIkJ1c6DePnBYYa1LIcwvUUUbmCmXPV7d4pk`
3. **Redémarrez Django** : Arrêtez et relancez le serveur
4. **Vérifiez les logs** : Messages d'erreur dans la console

### ❌ Si signature invalide
1. **Vérifiez le secret** : Doit être identique dans Stripe et settings.py
2. **Vérifiez l'environnement** : Mode test vs mode production
3. **Reconfigurez** : Supprimez et recréez le webhook

---

## 🎉 FÉLICITATIONS !

Une fois ces étapes terminées, votre système de paiement sera **100% automatique** et **fiable** !

Pour toute question, vérifiez les logs du serveur Django ou contactez le support technique.
