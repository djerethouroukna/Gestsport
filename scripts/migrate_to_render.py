#!/usr/bin/env python
"""
Script de migration des données vers Render PostgreSQL
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

# Configuration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connections
from django.core.management import call_command
from django.conf import settings
import psycopg2
import mysql.connector
from decimal import Decimal
from datetime import datetime

def migrate_mysql_to_postgresql():
    """Migration des données de MySQL vers PostgreSQL"""
    
    print("=== Migration MySQL vers PostgreSQL ===")
    
    # Connexion MySQL (source)
    mysql_config = {
        'host': config('DB_HOST', default='localhost'),
        'user': config('DB_USER', default='root'),
        'password': config('DB_PASSWORD', default=''),
        'database': config('DB_NAME', default='gestsport'),
        'port': config('DB_PORT', default='3306'),
    }
    
    try:
        mysql_conn = mysql.connector.connect(**mysql_config)
        mysql_cursor = mysql_conn.cursor()
        print("Connexion MySQL établie")
    except Exception as e:
        print(f"Erreur connexion MySQL: {e}")
        return False
    
    # Connexion PostgreSQL (cible)
    pg_config = {
        'host': os.environ.get('DATABASE_URL').split('@')[1].split('/')[0],
        'database': os.environ.get('DATABASE_URL').split('/')[-1],
        'user': os.environ.get('DATABASE_URL').split('@')[0].split('//')[1].split(':')[0],
        'password': os.environ.get('DATABASE_URL').split('@')[0].split(':')[2],
        'port': '5432',
    }
    
    try:
        pg_conn = psycopg2.connect(**pg_config)
        pg_cursor = pg_conn.cursor()
        print("Connexion PostgreSQL établie")
    except Exception as e:
        print(f"Erreur connexion PostgreSQL: {e}")
        return False
    
    # Liste des tables à migrer
    tables_to_migrate = [
        'users_user',
        'terrains_terrain', 
        'activities_activity',
        'reservations_reservation',
        'payments_payment',
        'notifications_notification',
        'chat_chatroom',
        'chat_message',
        'audit_auditlog',
        # Ajoutez d'autres tables selon vos besoins
    ]
    
    for table in tables_to_migrate:
        print(f"\nMigration de la table: {table}")
        
        try:
            # Récupérer les données MySQL
            mysql_cursor.execute(f"SELECT * FROM {table}")
            columns = [desc[0] for desc in mysql_cursor.description]
            rows = mysql_cursor.fetchall()
            
            if not rows:
                print(f"  - Pas de données à migrer pour {table}")
                continue
            
            # Créer la requête d'insertion PostgreSQL
            placeholders = ', '.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Insérer dans PostgreSQL
            for row in rows:
                # Conversion des types si nécessaire
                converted_row = []
                for value in row:
                    if isinstance(value, Decimal):
                        converted_row.append(float(value))
                    elif isinstance(value, datetime):
                        converted_row.append(value)
                    else:
                        converted_row.append(value)
                
                pg_cursor.execute(insert_query, converted_row)
            
            pg_conn.commit()
            print(f"  - {len(rows)} enregistrements migrés avec succès")
            
        except Exception as e:
            print(f"  - Erreur migration {table}: {e}")
            pg_conn.rollback()
    
    # Fermeture des connexions
    mysql_cursor.close()
    mysql_conn.close()
    pg_cursor.close()
    pg_conn.close()
    
    print("\n=== Migration terminée ===")
    return True

def run_django_migrations():
    """Exécuter les migrations Django"""
    print("Exécution des migrations Django...")
    
    try:
        # Créer les migrations
        call_command('makemigrations', interactive=False)
        
        # Appliquer les migrations
        call_command('migrate', interactive=False)
        
        # Créer le superutilisateur
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@gestsport.com',
                password='admin123',
                role='admin'
            )
            print("Superutilisateur créé: admin/admin123")
        
        # Collecter les fichiers statiques
        call_command('collectstatic', interactive=False)
        
        print("Migrations Django terminées avec succès")
        return True
        
    except Exception as e:
        print(f"Erreur migrations Django: {e}")
        return False

if __name__ == '__main__':
    print("Début de la migration vers Render PostgreSQL")
    
    # Étape 1: Exécuter les migrations Django
    if run_django_migrations():
        print("Étape 1: Migrations Django réussies")
        
        # Étape 2: Migrer les données (optionnel)
        # migrate_mysql_to_postgresql()
        
        print("Migration terminée avec succès!")
    else:
        print("Échec de la migration")
        sys.exit(1)
