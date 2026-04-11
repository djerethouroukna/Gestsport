# Créer un ticket valide pour tester l'API
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation
from terrains.models import Terrain
from users.models import User
from django.utils import timezone
from datetime import timedelta

print("=== CRÉATION TICKET VALIDE POUR TEST ===")

# Créer ou récupérer un utilisateur
user = User.objects.first()
if not user:
    print("❌ Aucun utilisateur trouvé")
    exit()

# Créer ou récupérer un terrain
terrain = Terrain.objects.first()
if not terrain:
    print("❌ Aucun terrain trouvé")
    exit()

# Créer une réservation valide
reservation, created = Reservation.objects.get_or_create(
    user=user,
    terrain=terrain,
    start_time=timezone.now(),
    end_time=timezone.now() + timedelta(hours=2),
    defaults={
        'status': 'confirmed',
        'total_amount': 50.00
    }
)

if created:
    print(f"✅ Réservation créée: {reservation.id}")
else:
    print(f"✅ Réservation existante: {reservation.id}")

# Créer un ticket valide
ticket, created = Ticket.objects.get_or_create(
    reservation=reservation,
    defaults={
        'ticket_number': f"TKT-TEST-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        'is_used': False
    }
)

if created:
    print(f"✅ Ticket créé: {ticket.ticket_number}")
    ticket.generate_qr_code()
    print(f"✅ QR code généré")
else:
    print(f"✅ Ticket existant: {ticket.ticket_number}")

print(f"\n=== TICKET CRÉÉ ===")
print(f"Numéro: {ticket.ticket_number}")
print(f"Utilisateur: {user.get_full_name() or user.username}")
print(f"Terrain: {terrain.name}")
print(f"Début: {reservation.start_time}")
print(f"Fin: {reservation.end_time}")
print(f"Durée: 2 heures")
print(f"Statut: {'Valide' if not ticket.is_used else 'Utilisé'}")
print(f"Valide: {ticket.is_valid}")

print(f"\n=== TEST SCAN ===")
print(f"Utilisez ce ticket pour tester l'API:")
print(f"QR Data: {ticket.ticket_number}")
print(f"Scanner ID: scanner_entrance_01")
print(f"Token: a9dc052f48d8098984e2f916673b51ed2e364929")

print(f"\n=== COMMANDE CURL ===")
print(f"curl -X POST http://127.0.0.1:8000/tickets/api/scanner/scan/ \\")
print(f"  -H \"Authorization: Token a9dc052f48d8098984e2f916673b51ed2e364929\" \\")
print(f"  -H \"Content-Type: application/json\" \\")
print(f"  -d '{{\"qr_data\": \"{ticket.ticket_number}\", \"scanner_id\": \"scanner_entrance_01\", \"location\": \"Entrée Principale\"}}'")

print(f"\n✅ Ticket prêt pour le test !")
