#!/usr/bin/env python
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from tickets.models import Ticket

# Créer une migration manuelle pour le champ created_at
def create_migration():
    """Crée une migration manuelle pour corriger le problème"""
    
    # Vérifier si la colonne created_at existe
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tickets_ticket' 
            AND column_name = 'created_at'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        if 'created_at' not in columns:
            # Ajouter la colonne created_at
            cursor.execute("""
                ALTER TABLE tickets_ticket 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            """)
            print("✅ Colonne created_at ajoutée")
        else:
            print("✅ Colonne created_at existe déjà")
    
    # Mettre à jour les enregistrements sans created_at
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE tickets_ticket 
            SET created_at = NOW() 
            WHERE created_at IS NULL
        """)
        print("✅ Valeurs created_at mises à jour")

if __name__ == '__main__':
    create_migration()
    print("✅ Migration terminée")
