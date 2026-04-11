# Guide de Migration vers Render

## Étape par Étape pour Déployer GestSport sur Render

### 1. Prérequis

- Compte Render (https://render.com)
- Compte Stripe (pour les paiements)
- Compte Email (pour les notifications)
- Repository GitHub avec votre code

### 2. Configuration du Repository GitHub

1. **Assurez-vous que votre code est sur GitHub**
   ```bash
   git add .
   git commit -m "Ready for Render deployment"
   git push origin main
   ```

2. **Vérifiez que votre `.env` n'est pas poussé**
   ```bash
   # .gitignore doit contenir:
   .env
   venv/
   __pycache__/
   *.pyc
   db.sqlite3
   ```

### 3. Création des Services sur Render

#### 3.1 Base de Données PostgreSQL

1. Connectez-vous à Render Dashboard
2. **New +** > **PostgreSQL**
3. **Configuration:**
   - **Name**: `gestsport-db`
   - **Database Name**: `gestsport`
   - **User**: `gestsport_user`
   - **Region**: Europe (ou la plus proche)
   - **Plan**: Free (pour commencer) ou Pro

4. **Notez les informations de connexion**

#### 3.2 Service Redis (pour WebSocket)

1. **New +** > **Redis**
2. **Configuration:**
   - **Name**: `gestsport-redis`
   - **Plan**: Free
   - **Region**: Même que la base de données

#### 3.3 Service Web Principal

1. **New +** > **Web Service**
2. **Connectez votre repository GitHub**
3. **Configuration:**
   - **Name**: `gestsport-web`
   - **Root Directory**: `backend` (si votre projet est dans un sous-dossier)
   - **Runtime**: Python 3
   - **Build Command**: 
     ```
     pip install -r requirements.txt && python manage.py collectstatic --noinput
     ```
   - **Start Command**: 
     ```
     gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
     ```
   - **Health Check Path**: `/health/`

#### 3.4 Variables d'Environnement

Dans les **Environment Variables** du service web:

| Variable | Valeur | Type |
|----------|-------|------|
| `DEBUG` | `False` | Plain |
| `SECRET_KEY` | `generate-secret` | Generate |
| `DATABASE_URL` | `connect-to-db` | From Database |
| `REDIS_URL` | `connect-to-redis` | From Service |
| `STRIPE_PUBLISHABLE_KEY` | `votre-clé-stripe` | Sync |
| `STRIPE_SECRET_KEY` | `votre-clé-stripe` | Sync |
| `STRIPE_WEBHOOK_SECRET` | `votre-webhook-secret` | Sync |
| `EMAIL_HOST_USER` | `votre-email` | Sync |
| `EMAIL_HOST_PASSWORD` | `votre-mot-de-passe` | Sync |

### 4. Configuration des Clés Stripe

1. **Connectez-vous à votre Dashboard Stripe**
2. **Récupérez vos clés de test**
3. **Ajoutez-les dans les variables d'environnement Render**

### 5. Déploiement Initial

1. **Déployez le service web**
   - Render va automatiquement:
     - Installer les dépendances
     - Exécuter les migrations
     - Collecter les fichiers statiques
     - Démarrer le serveur

2. **Vérifiez le déploiement**
   - Allez sur l'URL fournie par Render
   - Vous devriez voir votre application

### 6. Migration des Données (Optionnel)

Si vous avez des données existantes dans MySQL:

#### Option A: Script de Migration

1. **Utilisez le script fourni**
   ```bash
   python scripts/migrate_to_render.py
   ```

#### Option B: Export/Import Manuel

1. **Export MySQL**
   ```sql
   mysqldump -u root -p gestsport > gestsport_backup.sql
   ```

2. **Conversion vers PostgreSQL**
   - Utilisez des outils comme `pgloader` ou `pg_dump`

3. **Import PostgreSQL**
   ```bash
   psql -h votre-host-render -U gestsport_user -d gestsport < gestsport_converted.sql
   ```

### 7. Configuration du Domaine

1. **Ajoutez votre domaine personnalisé**
   - Dans les settings du service web
   - Ajoutez votre domaine (ex: gestsport.com)

2. **Configurez le DNS**
   - Ajoutez les enregistrements DNS fournis par Render

3. **HTTPS**
   - Render configure automatiquement HTTPS

### 8. Tests et Validation

#### 8.1 Tests de Base

1. **Page d'accueil**: `https://votre-app.render.com/`
2. **Admin**: `https://votre-app.render.com/admin/`
3. **API**: `https://votre-app.render.com/api/`

#### 8.2 Tests Fonctionnels

1. **Création de compte**
2. **Réservations**
3. **Paiements (test)**
4. **Notifications**
5. **WebSocket**

#### 8.3 Monitoring

1. **Logs Render**: Vérifiez les logs dans le dashboard
2. **Health Checks**: `/health/` endpoint
3. **Performance**: Utilisez les métriques Render

### 9. Configuration Production

#### 9.1 Variables d'Environnement Production

```bash
# Dans Render Environment Variables
DEBUG=False
ALLOWED_HOSTS=votre-domaine.com,votre-app.onrender.com
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

#### 9.2 Backup Automatique

Render offre des backups automatiques pour PostgreSQL. Configurez-les dans les settings de la base de données.

#### 9.3 Monitoring et Alertes

1. **Configurez les alertes Render**
2. **Surveillez les métriques**
3. **Configurez les logs externes (optionnel)**

### 10. Dépannage

#### Problèmes Communs

1. **Erreur 500**: Vérifiez les logs
2. **Base de données**: Vérifiez `DATABASE_URL`
3. **Fichiers statiques**: Vérifiez `collectstatic`
4. **WebSocket**: Vérifiez la configuration Redis

#### Commandes Utiles

```bash
# Forcer un rebuild
# Dans Render Dashboard: Manual Deploy

# Vérifier les migrations
python manage.py showmigrations

# Créer un superutilisateur
python manage.py createsuperuser

# Vérifier la configuration
python manage.py check --deploy
```

### 11. Coûts Estimés

| Service | Plan | Coût mensuel |
|---------|------|--------------|
| Web Service | Free | $0 |
| PostgreSQL | Free | $0 |
| Redis | Free | $0 |
| **Total** | **Free** | **$0** |

Pour la production:
- **Web Service**: $7-20/mois
- **PostgreSQL**: $7-25/mois
- **Redis**: $7-17/mois
- **Total**: $21-62/mois

### 12. Checklist Finale

- [ ] Repository GitHub propre
- [ ] Variables d'environnement configurées
- [ ] Base de données PostgreSQL créée
- [ ] Service Redis créé
- [ ] Clés Stripe configurées
- [ ] Domaine configuré
- [ ] HTTPS activé
- [ ] Tests passés
- [ ] Monitoring configuré
- [ ] Backup activé

### Support

- **Render Docs**: https://render.com/docs
- **Django Docs**: https://docs.djangoproject.com/
- **Stripe Docs**: https://stripe.com/docs

---

**Note**: Ce guide suppose que vous avez déjà une version fonctionnelle de votre application en local.
