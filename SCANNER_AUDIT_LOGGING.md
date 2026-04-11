# 🔍 **Scanner Manuel - Intégration Audit Log**

## ✅ **Nouvelle Fonctionnalité**

Le scanner manuel enregistre maintenant **automatiquement** chaque scan de ticket dans l'audit log, visible dans l'interface admin Django comme toutes les autres actions.

---

## 🎯 **Ce qui est enregistré**

### **Chaque scan de ticket génère une entrée dans l'audit log avec:**

#### **Informations principales:**
- ✅ **Action**: `SCAN` (nouveau type d'action)
- ✅ **Modèle**: `Ticket`
- ✅ **Représentation**: `Ticket TKT-XXXXXXXX`
- ✅ **Utilisateur**: Utilisateur authentifié du scanner
- ✅ **Timestamp**: Date/heure exacte du scan

#### **Détails du scan (dans `changes`):**
- ✅ **scan_result**: Résultat du scan (VALIDÉ, REJETÉ, FUTURE, etc.)
- ✅ **scanner_id**: ID du scanner (ex: "scanner_manual_01")
- ✅ **location**: Lieu du scan (ex: "Entrée Principale")
- ✅ **scan_details**: Détails spécifiques selon le résultat

#### **Métadonnées (dans `metadata`):**
- ✅ **scanner_type**: Type de scanner ("manual")
- ✅ **ticket_number**: Numéro du ticket scanné
- ✅ **scan_timestamp**: Timestamp ISO du scan
- ✅ **IP address**: Adresse IP du scanner
- ✅ **User agent**: User agent de l'application scanner

---

## 📊 **Exemples d'entrées dans l'audit log**

### **1. Ticket validé avec succès**
```
Utilisateur: Admin Test
Action: SCAN
Modèle: Ticket
Représentation: Ticket TKT-18D6BCE8
Timestamp: 2026-03-04 13:30:15

Changes: {
  "scan_result": "VALIDÉ",
  "scanner_id": "scanner_manual_01",
  "location": "Entrée Principale",
  "scan_details": {
    "ticket_number": "TKT-18D6BCE8",
    "terrain_name": "Terrain A",
    "date_formatted": "04/03/2026 14:00",
    "user_name": "Jean Dupont"
  }
}

Metadata: {
  "scanner_type": "manual",
  "ticket_number": "TKT-18D6BCE8",
  "scan_timestamp": "2026-03-04T13:30:15.123456"
}
```

### **2. Réservation future**
```
Utilisateur: Admin Test
Action: SCAN
Modèle: Ticket
Représentation: Ticket TKT-12345678
Timestamp: 2026-03-04 13:30:20

Changes: {
  "scan_result": "RÉSERVATION FUTURE",
  "scanner_id": "scanner_manual_01",
  "location": "Entrée Principale",
  "scan_details": {
    "error_code": "FUTURE_RESERVATION",
    "reservation_datetime": "2026-03-05 14:00:00",
    "start_time": "14:00:00",
    "end_time": "15:00:00"
  }
}
```

### **3. Ticket déjà utilisé**
```
Utilisateur: Admin Test
Action: SCAN
Modèle: Ticket
Représentation: Ticket TKT-87654321
Timestamp: 2026-03-04 13:30:25

Changes: {
  "scan_result": "DÉJÀ UTILISÉ",
  "scanner_id": "scanner_manual_01",
  "location": "Entrée Principale",
  "scan_details": {
    "error_code": "TICKET_ALREADY_USED",
    "used_at": "2026-03-04 12:15:30"
  }
}
```

---

## 🔧 **Configuration Technique**

### **Modifications apportées:**

#### **1. Modèle AuditLog (`audit/models.py`)**
```python
ACTION_CHOICES = [
    # ... autres actions
    ('SCAN', 'Scan Ticket'),  # ← Nouveau type d'action
    # ...
]
```

#### **2. API Audit (`audit/views.py`)**
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def audit_log_action(request):
    """API pour enregistrer une action dans l'audit log"""
    # Crée une entrée AuditLog avec les données reçues
```

#### **3. URLs Audit (`audit/urls.py`)**
```python
urlpatterns = [
    # ... autres URLs
    path('api/log/', views.audit_log_action, name='api_log'),
]
```

#### **4. Scanner Manuel (`simple_scanner/scanner_manual.py`)**
```python
def log_scan_to_audit(self, ticket_number, scan_result, scan_details):
    """Enregistre le scan dans l'audit log"""
    # Envoie les données du scan à l'API d'audit

# Appelé après chaque scan:
self.log_scan_to_audit(ticket_number, "VALIDÉ", scan_details)
```

---

## 🎯 **Cas d'utilisation enregistrés**

### **Tous les résultats de scan sont enregistrés:**

#### **✅ Succès:**
- `VALIDÉ` - Ticket validé avec succès
- Détails complets de la réservation

#### **🔮 Réservations futures:**
- `RÉSERVATION FUTURE` - Réservation pour jour futur
- Date/heure de la réservation future

#### **⏰ Expirations:**
- `RÉSERVATION EXPIRÉE` - Réservation expirée
- `RÉSERVATION TERMINÉE` - Réservation terminée
- Date/heure d'expiration

#### **🔄 Utilisations multiples:**
- `DÉJÀ UTILISÉ` - Ticket déjà scanné
- Date/heure de première utilisation

#### **❌ Erreurs:**
- `REJETÉ` - Ticket non trouvé ou invalide
- `ERREUR` - Erreur technique
- `HORS LIGNE` - API inaccessible

---

## 📱 **Visualisation dans l'Admin**

### **Où voir les logs:**

1. **Interface Admin Django**
   - Section "Audit" → "Audit logs"
   - Tableau complet avec tous les scans

2. **Dashboard Audit**
   - `/admin/audit/auditlog/`
   - Filtres disponibles par action, modèle, utilisateur

3. **Filtres spécifiques:**
   - Filtrer par `Action = SCAN`
   - Filtrer par `Modèle = Ticket`
   - Filtrer par `Utilisateur = Admin Test`

### **Colonnes disponibles:**
- **Utilisateur**: Qui a effectué le scan
- **Action**: Type "SCAN"
- **Modèle**: "Ticket"
- **Objet**: Numéro du ticket
- **Date/Heure**: Quand le scan a eu lieu
- **Adresse IP**: D'où le scan a été effectué
- **Changes**: Détails du résultat du scan
- **Metadata**: Informations supplémentaires

---

## 🚀 **Avantages**

### **Traçabilité complète:**
- ✅ **Qui**: Utilisateur qui a scanné
- ✅ **Quand**: Date/heure exacte
- ✅ **Où**: Lieu du scan
- ✅ **Quoi**: Ticket scanné
- ✅ **Comment**: Résultat du scan

### **Audit et sécurité:**
- ✅ **Historique complet** de tous les scans
- ✅ **Preuve** d'utilisation des tickets
- ✅ **Détection** d'anomalies
- ✅ **Statistiques** d'utilisation

### **Maintenance:**
- ✅ **Diagnostic** des problèmes de scan
- ✅ **Analyse** des tendances d'utilisation
- ✅ **Reporting** des activités de scan

---

## 🔍 **Recherche et Filtrage**

### **Exemples de requêtes utiles:**

#### **Tous les scans aujourd'hui:**
```
Action = SCAN
Date = Aujourd'hui
```

#### **Scans rejetés:**
```
Action = SCAN
Changes → scan_result = REJETÉ
```

#### **Scans par scanner spécifique:**
```
Action = SCAN
Changes → scanner_id = scanner_manual_01
```

#### **Scans avec erreurs:**
```
Action = SCAN
Changes → scan_result contains ERREUR
```

---

## 🎉 **Conclusion**

**Le scanner manuel est maintenant entièrement intégré au système d'audit !**

Chaque scan de ticket est enregistré avec:
- ✅ **Informations complètes** et détaillées
- ✅ **Traçabilité** totale
- ✅ **Intégration** parfaite avec l'admin Django
- ✅ **Performance** optimisée (non bloquant)

**Les administrateurs peuvent maintenant suivre toutes les activités de scan comme les autres actions du système !**

---

## 📞 **Support**

En cas de problème avec l'audit logging:
1. Vérifier les logs du scanner: `logs/scanner.log`
2. Vérifier la connectivité API: `/audit/api/log/`
3. Consulter les logs Django pour les erreurs
4. Vérifier les permissions de l'utilisateur scanner

**🎯 L'audit logging est automatique et transparent pour l'utilisateur du scanner !**
