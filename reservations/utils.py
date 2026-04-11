# reservations/utils.py
from decimal import Decimal

def calculate_reservation_amount(reservation):
    """
    Calcule le montant total d'une réservation de manière sécurisée
    Évite les erreurs de type Decimal/float
    
    Args:
        reservation: Objet Reservation avec duration_minutes et terrain.price_per_hour
        
    Returns:
        Decimal: Montant total calculé
    """
    try:
        # Calcul sécurisé avec Decimal uniquement
        duration_hours = Decimal(reservation.duration_minutes) / Decimal('60')
        price_per_hour = reservation.terrain.price_per_hour or Decimal('20.00')
        total_amount = duration_hours * price_per_hour
        
        return total_amount.quantize(Decimal('0.01'))  # 2 décimales
        
    except Exception as e:
        print(f"Erreur calcul montant réservation {reservation.id}: {e}")
        # Valeur par défaut en cas d'erreur
        return Decimal('0.00')


def get_reservation_duration_hours(reservation):
    """
    Retourne la durée en heures de la réservation
    
    Args:
        reservation: Objet Reservation
        
    Returns:
        Decimal: Durée en heures
    """
    try:
        return Decimal(reservation.duration_minutes) / Decimal('60')
    except Exception as e:
        print(f"Erreur calcul durée réservation {reservation.id}: {e}")
        return Decimal('0.00')


def format_currency(amount, currency='XOF'):
    """
    Formate un montant monétaire
    
    Args:
        amount: Decimal ou nombre
        currency: Code devise
        
    Returns:
        str: Montant formaté
    """
    try:
        if isinstance(amount, str):
            amount = Decimal(amount)
        elif not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
            
        formatted = f"{amount:,.2f} {currency}"
        return formatted.replace(',', ' ')  # Format français
    except Exception as e:
        print(f"Erreur formatage montant: {e}")
        return f"0.00 {currency}"
