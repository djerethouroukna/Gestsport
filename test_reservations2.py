import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestsport.settings')
import django
django.setup()

from django.utils import timezone
from datetime import datetime
from reservations.models import Reservation
from reservations.models import ReservationStatus

today = timezone.now().date()
today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

today_reservations = Reservation.objects.filter(
    start_time__gte=today_start,
    start_time__lte=today_end,
    status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING]
).count()

print('Aujourd\'hui:', today)
print('Début:', today_start)
print('Fin:', today_end)
print('Réservations aujourd\'hui:', today_reservations)
