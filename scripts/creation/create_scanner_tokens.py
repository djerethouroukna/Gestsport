# Script pour créer des tokens API pour les scanners
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import Permission
from users.models import User

print("=== CRÉATION TOKENS API POUR SCANNERS ===")

# 1. Créer le groupe "Scanners" s'il n'existe pas
try:
    scanners_group, created = Group.objects.get_or_create(name='Scanners')
    if created:
        print("✅ Groupe 'Scanners' créé")
    else:
        print("✅ Groupe 'Scanners' existe déjà")
except Exception as e:
    print(f"❌ Erreur création groupe: {e}")

# 2. Ajouter les permissions pour les scanners
try:
    # Permissions pour les scanners
    scan_permissions = []
    
    # Essayer de récupérer les permissions spécifiques
    try:
        scan_permissions.append(Permission.objects.get(codename='can_scan_tickets'))
        print("✅ Permission can_scan_tokens trouvée")
    except Permission.DoesNotExist:
        print("⚠️ Permission can_scan_tokens non trouvée")
    
    try:
        scan_permissions.append(Permission.objects.get(codename='can_view_scan_history'))
        print("✅ Permission can_view_scan_history trouvée")
    except Permission.DoesNotExist:
        print("⚠️ Permission can_view_scan_history non trouvée")
    
    try:
        scan_permissions.append(Permission.objects.get(codename='view_ticket'))
        print("✅ Permission view_ticket trouvée")
    except Permission.DoesNotExist:
        print("⚠️ Permission view_ticket non trouvée")
    
    try:
        scan_permissions.append(Permission.objects.get(codename='change_ticket'))
        print("✅ Permission change_ticket trouvée")
    except Permission.DoesNotExist:
        print("⚠️ Permission change_ticket non trouvée")
    
    # Ajouter les permissions au groupe
    for permission in scan_permissions:
        scanners_group.permissions.add(permission)
    
    print("✅ Permissions ajoutées au groupe 'Scanners'")
except Exception as e:
    print(f"❌ Erreur ajout permissions: {e}")

# 3. Créer un utilisateur scanner
try:
    # Créer l'utilisateur scanner
    scanner_user, created = User.objects.get_or_create(
        email='scanner@gestsport.com',
        defaults={
            'first_name': 'Scanner',
            'last_name': 'User',
            'is_active': True,
            'is_staff': False,
        }
    )
    if created:
        scanner_user.set_password('scanner_password_123')
        scanner_user.save()
        print("✅ Utilisateur scanner créé")
    else:
        print("✅ Utilisateur scanner existe déjà")
    
    # Ajouter l'utilisateur au groupe scanners
    scanner_user.groups.add(scanners_group)
    print("✅ Utilisateur scanner ajouté au groupe")
    
except Exception as e:
    print(f"❌ Erreur création utilisateur scanner: {e}")

# 4. Créer ou récupérer le token pour l'utilisateur scanner
try:
    token, created = Token.objects.get_or_create(user=scanner_user)
    print(f"✅ Token API créé: {token.key}")
    print(f"   Utilisateur: {scanner_user.username}")
    print(f"   Token: {token.key}")
    
except Exception as e:
    print(f"❌ Erreur création token: {e}")

# 5. Créer des tokens pour plusieurs scanners
scanners_data = [
    {
        'username': 'scanner_entrance_01',
        'email': 'scanner.entrance.01@gestsport.com',
        'first_name': 'Scanner',
        'last_name': 'Entrance 01',
        'location': 'Entrée Principale'
    },
    {
        'username': 'scanner_entrance_02',
        'email': 'scanner.entrance.02@gestsport.com',
        'first_name': 'Scanner',
        'last_name': 'Entrance 02',
        'location': 'Entrée Secondaire'
    },
    {
        'username': 'scanner_mobile_01',
        'email': 'scanner.mobile.01@gestsport.com',
        'first_name': 'Scanner',
        'last_name': 'Mobile 01',
        'location': 'Scanner Mobile'
    }
]

print(f"\n=== CRÉATION TOKENS MULTIPLES ===")

for scanner_info in scanners_data:
    try:
        # Créer l'utilisateur scanner
        scanner_user, created = User.objects.get_or_create(
            email=scanner_info['email'],
            defaults={
                'first_name': scanner_info['first_name'],
                'last_name': scanner_info['last_name'],
                'is_active': True,
                'is_staff': False,
            }
        )
        
        if created:
            scanner_user.set_password('scanner_password_123')
            scanner_user.save()
            print(f"✅ Utilisateur {scanner_info['username']} créé")
        
        # Ajouter au groupe scanners
        scanner_user.groups.add(scanners_group)
        
        # Créer le token
        token, created = Token.objects.get_or_create(user=scanner_user)
        
        print(f"   Token: {token.key}")
        print(f"   Scanner ID: {scanner_info['username']}")
        print(f"   Location: {scanner_info['location']}")
        print(f"   ---")
        
    except Exception as e:
        print(f"❌ Erreur création {scanner_info['username']}: {e}")

print(f"\n=== RÉSUMÉ ===")
print(f"✅ Groupe 'Scanners' configuré")
print(f"✅ Permissions attribuées")
print(f"✅ Utilisateurs scanners créés")
print(f"✅ Tokens API générés")

print(f"\n=== INSTRUCTIONS ===")
print(f"1. Utilisez ces tokens dans vos applications scanner")
print(f"2. Ajoutez le header: Authorization: Token VOTRE_TOKEN")
print(f"3. Appelez l'API: POST /tickets/api/scanner/scan/")
print(f"4. Documentation: http://127.0.0.1:8000/api/docs/")

print(f"\n=== EXEMPLE D'UTILISATION ===")
print(f"curl -X POST http://127.0.0.1:8000/tickets/api/scanner/scan/ \\")
print(f"  -H \"Authorization: Token VOTRE_TOKEN_ICI\" \\")
print(f"  -H \"Content-Type: application/json\" \\")
print(f"  -d '{{\"qr_data\": \"TKT-XXXXXXXX\", \"scanner_id\": \"scanner_entrance_01\", \"location\": \"Entrée Principale\"}}'")

print(f"\n✅ Configuration terminée !")
