import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import Ticket
from reservations.models import Reservation

# Forcer la génération du QR code pour le ticket de la réservation 42
try:
    reservation = Reservation.objects.get(id=42)
    ticket = Ticket.objects.get(reservation=reservation)
    
    print(f'Ticket: {ticket.ticket_number}')
    print(f'QR Code avant: {ticket.qr_code}')
    
    # Forcer la génération du QR code
    if not ticket.qr_code:
        print('Génération du QR code...')
        ticket.generate_qr_code_separated()
        
        # Recharger le ticket depuis la BD
        ticket.refresh_from_db()
        print(f'QR Code après: {ticket.qr_code}')
        
        if ticket.qr_code:
            print('QR Code généré avec succès!')
        else:
            print('ERREUR: QR Code non généré')
    else:
        print('QR Code existe déjà')
        
except Exception as e:
    print(f'Erreur: {e}')
    import traceback
    traceback.print_exc()
