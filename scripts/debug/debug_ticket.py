import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation
from django.conf import settings

# Vérifier le ticket pour la réservation 42
try:
    reservation = Reservation.objects.get(id=42)
    ticket = Ticket.objects.get(reservation=reservation)
    
    print(f'Ticket: {ticket.ticket_number}')
    print(f'QR Code: {ticket.qr_code}')
    
    if ticket.qr_code:
        qr_path = os.path.join(settings.MEDIA_ROOT, ticket.qr_code.name)
        print(f'Chemin QR: {qr_path}')
        print(f'Fichier existe: {os.path.exists(qr_path)}')
        
        if os.path.exists(qr_path):
            size = os.path.getsize(qr_path)
            print(f'Taille fichier: {size} octets')
    else:
        print('QR Code non généré')
        
    # Vérifier les heures
    print(f'\\nHeures dans la réservation:')
    print(f'Start time: {reservation.start_time}')
    print(f'End time: {reservation.end_time}')
    print(f'Timezone: {reservation.start_time.tzinfo}')
    
    # Formatter les heures
    print(f'\\nHeures formatées:')
    print(f'Début: {reservation.start_time.strftime("%H:%M")}')
    print(f'Fin: {reservation.end_time.strftime("%H:%M")}')
    
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
