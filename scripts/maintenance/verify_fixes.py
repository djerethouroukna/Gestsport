import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation
from django.conf import settings
from django.utils import timezone

# Vérifier les heures après correction
try:
    reservation = Reservation.objects.get(id=42)
    ticket = Ticket.objects.get(reservation=reservation)
    
    print(f'Ticket: {ticket.ticket_number}')
    print(f'QR Code: {ticket.qr_code}')
    
    # Vérifier les heures avec timezone
    print(f'\\n=== HEURES AVEC TIMEZONE ===')
    print(f'Start time (UTC): {reservation.start_time}')
    print(f'Start time (local): {reservation.start_time.astimezone()}')
    print(f'End time (UTC): {reservation.end_time}')
    print(f'End time (local): {reservation.end_time.astimezone()}')
    
    # Formatter les heures comme dans le PDF
    print(f'\\n=== HEURES FORMATÉES POUR PDF ===')
    print(f'Date: {reservation.start_time.astimezone().strftime("%d/%m/%Y")}')
    print(f'Heure: {reservation.start_time.astimezone().strftime("%H:%M")} - {reservation.end_time.astimezone().strftime("%H:%M")}')
    
    # Vérifier le QR code
    if ticket.qr_code:
        qr_path = os.path.join(settings.MEDIA_ROOT, ticket.qr_code.name)
        print(f'\\nQR Code: {qr_path}')
        print(f'Fichier existe: {os.path.exists(qr_path)}')
        if os.path.exists(qr_path):
            size = os.path.getsize(qr_path)
            print(f'Taille: {size} octets')
    
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
