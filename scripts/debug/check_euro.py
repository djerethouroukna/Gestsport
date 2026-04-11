#!/usr/bin/env python3
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from reservations.models import Reservation

User = get_user_model()

try:
    reservation = Reservation.objects.get(id=27)
    print(f'Reservation ID 27: {reservation.terrain.name}')
    
    admin = User.objects.filter(role='admin').first()
    if not admin:
        print('Aucun admin trouve')
        exit()
    
    print(f'Admin: {admin.email}')
    
    client = Client()
    success = client.login(email=admin.email, password='admin123')
    print(f'Login success: {success}')
    
    if success:
        response = client.get('/reservations/admin/27/')
        content = response.content.decode('utf-8')
        
        print(f'Status HTTP: {response.status_code}')
        
        euro_count = content.count('€')
        fcfa_count = content.count('FCFA')
        xof_count = content.count('XOF')
        
        print(f'Symboles €: {euro_count}')
        print(f'Occurrences FCFA: {fcfa_count}')
        print(f'Occurrences XOF: {xof_count}')
        
        if euro_count == 0:
            print('SUCCES: Aucun symbole € trouve')
        else:
            print(f'ERREUR: {euro_count} symboles € trouves')
            
        if fcfa_count > 0:
            print('SUCCES: FCFA est bien utilise')
        
except Exception as e:
    print(f'Erreur: {e}')
