#!/usr/bin/env python3
# ====================================================================
# SCRIPT AUTOMATIQUE POUR CRÉER L'UTILISATEUR SCAN_USER
# ====================================================================

import psycopg2
import sys
from config.settings import DATABASES

def create_scan_user():
    """Crée l'utilisateur scan_user dans PostgreSQL"""
    
    print("=" * 60)
    print("   CRÉATION AUTOMATIQUE DE L'UTILISATEUR SCAN_USER")
    print("=" * 60)
    
    # Configuration de la base de données (utilisateur postgres)
    db_config = DATABASES['default']
    
    # Connexion en tant que postgres pour créer l'utilisateur
    try:
        print("🔌 Connexion à PostgreSQL en tant que postgres...")
        
        conn = psycopg2.connect(
            host=db_config['HOST'],
            port=db_config['PORT'],
            database='postgres',  # Base par défaut pour créer des utilisateurs
            user='postgres',      # Utilisateur admin
            password=db_config['PASSWORD']
        )
        
        conn.autocommit = True  # Nécessaire pour CREATE USER
        cursor = conn.cursor()
        
        print("✅ Connexion réussie")
        
        # 1. Créer l'utilisateur scan_user
        print("👤 Création de l'utilisateur scan_user...")
        
        try:
            cursor.execute(f"CREATE USER scan_user WITH PASSWORD '{db_config['PASSWORD']}'")
            print(" Utilisateur scan_user créé")
        except psycopg2.errors.DuplicateObject:
            print(" L'utilisateur scan_user existe déjà")
        
        # 2. Donner les permissions sur la base gestsport
        print(" Attribution des permissions...")
        
        permissions = [
            f"GRANT CONNECT ON DATABASE {db_config['NAME']} TO scan_user",
            "GRANT USAGE ON SCHEMA public TO scan_user",
            "GRANT SELECT ON ALL TABLES IN SCHEMA public TO scan_user",
            "GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO scan_user",
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO scan_user"
        ]
        
        for permission in permissions:
            try:
                cursor.execute(permission)
                print(f"✅ Permission accordée: {permission.split()[0]}")
            except Exception as e:
                print(f"⚠️ Permission déjà existante ou erreur: {e}")
        
        # 4. Donner les permissions sur les tables spécifiques du scanner
        permissions_tables = [
            "GRANT SELECT ON tickets_ticket TO scan_user",
            "GRANT SELECT ON reservations_reservation TO scan_user", 
            "GRANT SELECT ON users_user TO scan_user",
            "GRANT SELECT ON terrains_terrain TO scan_user",
            "GRANT SELECT ON activities_activity TO scan_user",
            "GRANT SELECT ON tickets_scan TO scan_user"
        ]
        
        for permission in permissions_tables:
            try:
                cursor.execute(permission)
                print(f"✅ Table permission: {permission.split()[2]}")
            except Exception as e:
                print(f"⚠️ Table permission error: {e}")
        
        # 5. Vérification
        print("\n🔍 Vérification des permissions...")
        cursor.execute("SELECT usename FROM pg_user WHERE usename = 'scan_user'")
        
        # Afficher les informations de l'utilisateur
        cursor.execute("""
            SELECT usename, usesuper, usecreatedb
            FROM pg_user 
            WHERE usename = 'scan_user'
        """)
        
        user_info = cursor.fetchone()
        if user_info:
            print(f"✅ Utilisateur scan_user vérifié:")
            print(f"   - Nom: {user_info[0]}")
            print(f"   - Superuser: {user_info[1]}")
            print(f"   - Créateur DB: {user_info[2]}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎉 UTILISATEUR SCAN_USER CRÉÉ AVEC SUCCÈS!")
        print("=" * 60)
        print("L'utilisateur scan_user peut maintenant se connecter à la base")
        print("avec les permissions de lecture nécessaires pour le scanner.")
        print("=" * 60)
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Erreur de connexion PostgreSQL: {e}")
        print("\nVérifiez que:")
        print("  1. PostgreSQL est en cours d'exécution")
        print("  2. L'utilisateur postgres existe")
        print("  3. Le mot de passe postgres est correct")
        print("  4. Le port 5432 est accessible")
        return False
        
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def test_scan_user_connection():
    """Teste la connexion de scan_user"""
    
    print("\n🧪 Test de connexion avec scan_user...")
    
    try:
        # Configuration pour scan_user
        db_config = DATABASES['default']
        
        conn = psycopg2.connect(
            host=db_config['HOST'],
            port=db_config['PORT'],
            database=db_config['NAME'],
            user='scan_user',
            password=db_config['PASSWORD']
        )
        
        cursor = conn.cursor()
        
        # Test de lecture
        cursor.execute("SELECT COUNT(*) FROM tickets_ticket LIMIT 1")
        count = cursor.fetchone()[0]
        
        print(f"✅ Connexion scan_user réussie")
        print(f"📊 Tickets trouvés: {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur connexion scan_user: {e}")
        return False

def main():
    """Fonction principale"""
    
    # Créer l'utilisateur
    if create_scan_user():
        # Tester la connexion
        if test_scan_user_connection():
            print("\n🎯 Configuration terminée! Le scanner peut maintenant se connecter.")
            
            # Lancer les tests du scanner
            print("\n🔄 Lancement des tests du scanner...")
            import subprocess
            import os
            
            os.chdir("simple_scanner")
            result = subprocess.run([sys.executable, "test_scanner.py"], 
                                  capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print("Erreurs:", result.stderr)
        else:
            print("\n❌ La connexion scan_user a échoué")
    else:
        print("\n❌ La création de l'utilisateur a échoué")

if __name__ == "__main__":
    main()
