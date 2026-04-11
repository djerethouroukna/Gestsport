import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from users.models import User

print("=== VÉRIFICATION UTILISATEURS ===")

users = User.objects.all()
print(f"Total utilisateurs: {users.count()}")

for user in users:
    print(f"User: {user.username} - Role: {user.role} - Email: {user.email}")

# Trouver un coach avec un vrai username
coaches = User.objects.filter(role='coach')
print(f"\nCoaches: {coaches.count()}")

for coach in coaches:
    print(f"Coach: {coach.username} - {coach.get_full_name()} - {coach.email}")

# Créer un coach de test si nécessaire
if not coaches.exists():
    print("\nCréation d'un coach de test...")
    coach = User.objects.create_user(
        username='testcoach',
        email='testcoach@example.com',
        password='testpass123',
        role='coach',
        first_name='Test',
        last_name='Coach'
    )
    print(f"✅ Coach test créé: {coach.username}")
    print("Mot de passe: testpass123")
