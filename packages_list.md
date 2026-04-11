# 📦 Liste complète des packages installés dans le projet GestSport

## 🎯 **Packages principaux du projet Django**

### **Framework Django & Core**
- `Django==4.2.7` - Framework web principal
- `djangorestframework==3.14.0` - API REST pour Django
- `djangorestframework-simplejwt==5.3.0` - Authentification JWT
- `django-cors-headers==4.3.1` - Gestion CORS
- `django-debug-toolbar==4.2.0` - Toolbar de debug
- `django-filter==23.5` - Filtrage avancé
- `django-health-check==3.17.0` - Monitoring santé
- `django-webpush==0.3.6` - Notifications push web

### **Base de données**
- `mysql-connector-python==8.2.0` - Connecteur MySQL
- `mysqlclient==2.2.0` - Client MySQL
- `psycopg2-binary==2.9.11` - Connecteur PostgreSQL

### **WebSocket & Temps réel**
- `channels==4.3.2` - WebSocket pour Django
- `channels_redis==4.3.0` - Redis pour Channels
- `redis==7.1.0` - Base de données Redis

### **API Documentation**
- `drf-spectacular==0.29.0` - Documentation API OpenAPI/Swagger
- `drf-yasg==1.21.7` - Génération schéma API

## 🔧 **Applications Django du projet**

### **Modules métiers**
- `users` - Gestion des utilisateurs (rôles: admin, coach, player)
- `terrains` - Gestion des terrains de sport
- `activities` - Gestion des activités et entraînements
- `reservations` - Gestion des réservations de terrains
- `tickets` - Système de tickets/support
- `chat` - Messagerie instantanée
- `notifications` - Système de notifications
- `payments` - Gestion des paiements (Stripe)
- `timeslots` - Créneaux horaires
- `pricing` - Gestion des tarifs
- `subscriptions` - Abonnements
- `waitinglist` - Liste d'attente
- `audit` - Système d'audit et logs
- `reports` - Rapports et exportations PDF

## 💳 **Paiements & Services externes**

### **Stripe & Paiements**
- `stripe==14.3.0` - API Stripe pour paiements
- `twilio==9.10.1` - SMS et notifications

### **Communications**
- `requests==2.31.0` - Client HTTP
- `email-validator==2.3.0` - Validation emails

## 📱 **Applications Mobile & Scanner**

### **Kivy - Interface mobile**
- `Kivy==2.2.1` - Framework Python pour mobile
- `kivymd==1.1.1` - Material Design pour Kivy
- `Kivy-Garden==0.1.5` - Composants Kivy
- `PyQt5==5.15.11` - Interface GUI alternative
- `PyQt5-Qt5==5.15.2` - Qt5 pour PyQt5

### **Scanner QR Code**
- `opencv-python==4.13.0.92` - Traitement d'images
- `Pillow==10.0.0` - Manipulation d'images
- `pyzbar==0.1.9` - Lecture QR codes
- `qrcode==7.4.2` - Génération QR codes

## 🔐 **Sécurité & Cryptographie**

- `cryptography==46.0.3` - Cryptographie avancée
- `PyJWT==2.10.1` - Tokens JWT
- `pyOpenSSL==25.3.0` - Interface OpenSSL Python

## 📊 **Traitement de données & Export**

### **PDF & Documents**
- `reportlab==4.0.8` - Génération PDF
- `xhtml2pdf==0.2.13` - HTML vers PDF
- `pypdf==6.4.0` - Manipulation PDF

### **Excel & Tableurs**
- `openpyxl==3.1.5` - Fichiers Excel
- `xlsxwriter==3.2.9` - Écriture Excel

### **Images & Graphiques**
- `svglib==1.5.1` - SVG vers PDF
- `weasyprint==68.0` - HTML/CSS vers PDF

## 🌐 **API & Services Web**

### **FastAPI & Services**
- `fastapi==0.104.1` - API alternative (probablement pour scanners)
- `uvicorn==0.24.0` - Serveur ASGI
- `starlette==0.27.0` - Framework ASGI

### **WebSocket & Réseau**
- `aiohttp==3.13.3` - Client HTTP async
- `websockets==12.0` - WebSocket client
- `autobahn==24.4.2` - WebSocket

## 🔧 **Outils de développement**

### **Validation & Parsing**
- `pydantic==2.12.5` - Validation de données
- `jsonschema==4.26.0` - Validation JSON
- `sqlparse==0.5.3` - Parsing SQL

### **Performance & Monitoring**
- `psutil==7.2.2` - Monitoring système
- `propcache==0.4.1` - Cache de propriétés

## 🌍 **Internationalisation & Texte**

### **Support multilingue**
- `python-bidi==0.6.7` - Texte bidirectionnel (Arabe)
- `arabic-reshaper==3.0.0` - Formattage arabe
- `pyphen==0.17.2` - Césure textuelle

### **Temps & Dates**
- `python-dateutil==2.8.2` - Manipulation dates
- `pytz==2025.2` - Fuseaux horaires
- `tzlocal==5.3.1` - Temps local

## 🎨 **Interface & Frontend**

### **HTML/CSS**
- `tinycss2==1.5.1` - Minification CSS
- `cssselect2==0.8.0` - Sélecteurs CSS

### **Templates & Rendering**
- `Jinja2==3.1.6` - Moteur de templates
- `MarkupSafe==3.0.3` - Sécurité templates

## 📦 **Gestion des packages**

### **Outils système**
- `pip==26.0.1` - Gestionnaire packages Python
- `setuptools==57.4.0` - Installation packages
- `packaging==25.0` - Métadonnées packages

### **Environnement**
- `python-dotenv==1.0.0` - Variables environnement
- `six==1.17.0` - Compatibilité Python 2/3

## 🔧 **Dépendances système**

### **Windows**
- `pypiwin32==223` - API Windows
- `pywin32==311` - Interface Windows Python

### **Compatibilité**
- `typing_extensions==4.15.0` - Extensions typing
- `typing-inspection==0.4.2` - Inspection typing

---

## 📈 **Statistiques**

- **Total packages installés** : ~140 packages
- **Framework principal** : Django 4.2.7
- **Base de données principale** : MySQL
- **API principale** : Django REST Framework
- **Interface mobile** : Kivy
- **Paiements** : Stripe
- **WebSocket** : Django Channels + Redis

## 🎯 **Architecture du projet**

```
Frontend Web (Django Templates)
├── Dashboard Admin
├── Réservations & Terrains  
├── Activités & Coaching
├── Paiements Stripe
├── Notifications temps réel
└── Rapports PDF

Backend API (Django REST)
├── Authentification JWT
├── WebSocket (Channels)
├── Notifications push
└── API Scanner

Mobile App (Kivy)
├── Scanner QR Code
├── Validation tickets
└── Synchronisation API

Services externes
├── Stripe (paiements)
├── Twilio (SMS)
├── Redis (WebSocket)
└── MySQL (base de données)
```

*Généré le 11/04/2026 - Projet GestSport*
