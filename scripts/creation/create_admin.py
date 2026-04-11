#!/usr/bin/env python
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Vérifier si l'admin existe déjà
if User.objects.filter(email='admin@gestsport.com').exists():
    print('ℹ️  Compte admin existe déjà: admin@gestsport.com')
    admin = User.objects.get(email='admin@gestsport.com')
    print(f'   Rôle: {admin.role}')
    print(f'   Staff: {admin.is_staff}')
else:
    # Créer le compte admin
    admin = User.objects.create_user(
        username='admin@gestsport.com',
        email='admin@gestsport.com',
        password='Admin123!',
        first_name='Admin',
        last_name='User'
    )
    admin.role = 'admin'
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    
    print('✅ Compte admin créé avec succès!')
    print('   Email: admin@gestsport.com')
    print('   Mot de passe: Admin123!')
    print('   Rôle: admin')

print('\n🔗 Vous pouvez maintenant vous connecter:')
print('   URL: http://localhost:5173/login')
print('   Email: admin@gestsport.com')
print('   Mot de passe: Admin123!')
