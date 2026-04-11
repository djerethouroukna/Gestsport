from django.db.models import Sum
from decimal import Decimal
from payments.models import Payment
from reservations.models import Reservation


def get_accurate_reservation_stats(terrain_id=None, start_date=None, end_date=None):
    """
    Calcule des statistiques de réservations précises et cohérentes
    """
    
    # 1. Filtrer uniquement les réservations confirmées (CORRECTION: status='completed')
    reservations = Reservation.objects.filter(status='completed')
    
    # 2. Obtenir les paiements validés uniquement
    completed_payments = Payment.objects.filter(
        status__in=['completed', 'simulated', 'paid']
    )
    
    # 3. Lier réservations et paiements validés
    if terrain_id:
        reservations = reservations.filter(terrain_id=terrain_id)
        completed_payments = completed_payments.filter(reservation__terrain_id=terrain_id)
    
    if start_date:
        reservations = reservations.filter(start_time__date__gte=start_date)
        completed_payments = completed_payments.filter(reservation__start_time__date__gte=start_date)
    
    if end_date:
        reservations = reservations.filter(start_time__date__lte=end_date)
        completed_payments = completed_payments.filter(reservation__start_time__date__lte=end_date)
    
    # 4. Obtenir les IDs de réservations avec paiements validés
    valid_reservation_ids = completed_payments.values_list('reservation_id')
    
    # 5. Filtrer uniquement les réservations avec paiements validés
    final_reservations = reservations.filter(id__in=valid_reservation_ids)
    
    # 6. Calculer les statistiques CORRECTES
    total_reservations = final_reservations.count()
    total_revenue = completed_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    return {
        'reservations': final_reservations.select_related('terrain', 'user'),
        'total_reservations': total_reservations,
        'total_revenue': total_revenue,
        'completed_payments': completed_payments.select_related('reservation', 'user')
    }


def get_terrain_statistics(reservations, completed_payments):
    """
    Calcule les statistiques par terrain avec les vrais montants payés
    """
    terrain_stats = []
    
    for terrain in Terrain.objects.all():
        terrain_reservations = reservations.filter(terrain=terrain)
        terrain_payments = completed_payments.filter(reservation__terrain=terrain)
        
        terrain_total = terrain_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        terrain_count = terrain_reservations.count()
        
        if terrain_count > 0:
            terrain_stats.append({
                'terrain': terrain,
                'reservations_count': terrain_count,
                'total_amount': terrain_total,
                'average_amount': terrain_total / terrain_count
            })
    
    return sorted(terrain_stats, key=lambda x: x['total_amount'], reverse=True)
