#!/usr/bin/env python
import os
import sys
import django

# Ajouter le répertoire parent au chemin Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User

def create_test_users():
    """Crée des utilisateurs de test pour le développement"""
    
    # Supprimer les utilisateurs existants (optionnel)
    # User.objects.all().delete()
    
    # Créer un admin
    if not User.objects.filter(email='admin@gestsport.com').exists():
        admin = User.objects.create_user(
            email='admin@gestsport.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        print(f"✅ Admin créé: {admin.email}")
    else:
        print("ℹ️ Admin existe déjà")
    
    # Créer des coaches
    coaches_data = [
        {'email': 'coach1@gestsport.com', 'first_name': 'Jean', 'last_name': 'Dupont'},
        {'email': 'coach2@gestsport.com', 'first_name': 'Marie', 'last_name': 'Martin'},
    ]
    
    for coach_data in coaches_data:
        if not User.objects.filter(email=coach_data['email']).exists():
            coach = User.objects.create_user(
                email=coach_data['email'],
                password='coach123',
                first_name=coach_data['first_name'],
                last_name=coach_data['last_name'],
                role=User.Role.COACH,
                is_active=True
            )
            print(f"✅ Coach créé: {coach.email}")
        else:
            print(f"ℹ️ Coach existe déjà: {coach_data['email']}")
    
    # Créer des joueurs
    players_data = [
        {'email': 'player1@gestsport.com', 'first_name': 'Pierre', 'last_name': 'Durand'},
        {'email': 'player2@gestsport.com', 'first_name': 'Sophie', 'last_name': 'Lefebvre'},
        {'email': 'player3@gestsport.com', 'first_name': 'Thomas', 'last_name': 'Bernard'},
        {'email': 'player4@gestsport.com', 'first_name': 'Camille', 'last_name': 'Petit'},
        {'email': 'player5@gestsport.com', 'first_name': 'Nicolas', 'last_name': 'Robert'},
    ]
    
    for player_data in players_data:
        if not User.objects.filter(email=player_data['email']).exists():
            player = User.objects.create_user(
                email=player_data['email'],
                password='player123',
                first_name=player_data['first_name'],
                last_name=player_data['last_name'],
                role=User.Role.PLAYER,
                is_active=True
            )
            print(f"✅ Joueur créé: {player.email}")
        else:
            print(f"ℹ️ Joueur existe déjà: {player_data['email']}")
    
    # Afficher le résumé
    total_users = User.objects.count()
    admin_count = User.objects.filter(role=User.Role.ADMIN).count()
    coach_count = User.objects.filter(role=User.Role.COACH).count()
    player_count = User.objects.filter(role=User.Role.PLAYER).count()
    
    print(f"\n📊 Résumé des utilisateurs:")
    print(f"   Total: {total_users}")
    print(f"   Admins: {admin_count}")
    print(f"   Coaches: {coach_count}")
    print(f"   Joueurs: {player_count}")
    
    print(f"\n🔑 Identifiants de test:")
    print(f"   Admin: admin@gestsport.com / admin123")
    print(f"   Coach: coach1@gestsport.com / coach123")
    print(f"   Player: player1@gestsport.com / player123")

if __name__ == '__main__':
    create_test_users()
