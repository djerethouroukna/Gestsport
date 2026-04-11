#!/usr/bin/env python3
# ==============================================================================
# TROUVER LES TICKETS VALIDES POUR LE SCANNER
# ==============================================================================

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from tickets.models import Ticket
from django.utils import timezone

def find_valid_tickets():
    """Trouve les tickets qui peuvent être scannés maintenant"""
    
    print("=" * 60)
    print("   TICKETS VALIDES POUR SCANNER MAINTENANT")
    print("=" * 60)
    
    now = timezone.now()
    
    # 1. Tickets non utilisés
    unused_tickets = Ticket.objects.filter(is_used=False)
    print(f"📊 Tickets non utilisés: {unused_tickets.count()}")
    
    # 2. Tickets avec réservation valide
    valid_tickets = []
    for ticket in unused_tickets:
        reservation = ticket.reservation
        
        # Autoriser jusqu'à 2 heures avant
        if reservation.start_time <= now + timezone.timedelta(hours=2):
            if reservation.end_time >= now:
                valid_tickets.append(ticket)
    
    print(f"✅ Tickets valides maintenant: {len(valid_tickets)}")
    
    # 3. Afficher les détails
    if valid_tickets:
        print("\n🎫 TICKETS DISPONIBLES POUR SCAN:")
        print("-" * 60)
        
        for i, ticket in enumerate(valid_tickets[:10], 1):  # Limiter à 10
            reservation = ticket.reservation
            status = "✅ DISPONIBLE"
            
            if reservation.start_time > now:
                time_until = reservation.start_time - now
                status = f"⏰ DANS {time_until.total_seconds()/3600:.1f}H"
            
            print(f"{i}. {ticket.ticket_number}")
            print(f"   Utilisateur: {reservation.user.get_full_name() or reservation.user.username}")
            print(f"   Terrain: {reservation.terrain.name}")
            print(f"   Début: {reservation.start_time.strftime('%H:%M')}")
            print(f"   Fin: {reservation.end_time.strftime('%H:%M')}")
            print(f"   Statut: {status}")
            print()
    
    else:
        print("\n❌ Aucun ticket valide pour le moment")
        print("   Créez des réservations ou attendez les heures de début")
    
    # 4. Tickets futurs (prochains)
    future_tickets = []
    for ticket in unused_tickets:
        reservation = ticket.reservation
        if reservation.start_time > now + timezone.timedelta(hours=2):
            future_tickets.append(ticket)
    
    if future_tickets:
        print(f"\n📅 PROCHAINS TICKETS (plus de 2h):")
        print("-" * 60)
        
        for ticket in future_tickets[:5]:
            reservation = ticket.reservation
            time_until = reservation.start_time - now
            print(f"• {ticket.ticket_number} - Dans {time_until.total_seconds()/3600:.1f}h")
    
    # 5. Tickets utilisés
    used_tickets = Ticket.objects.filter(is_used=True)
    print(f"\n📈 Tickets déjà utilisés: {used_tickets.count()}")
    
    if used_tickets:
        print("   Derniers utilisés:")
        for ticket in used_tickets.order_by('-used_at')[:3]:
            print(f"   • {ticket.ticket_number} à {ticket.used_at.strftime('%H:%M')}")
    
    print("\n" + "=" * 60)
    print("🎯 UTILISEZ CES NUMÉROS POUR TESTER LE SCANNER:")
    for ticket in valid_tickets[:3]:
        print(f"   {ticket.ticket_number}")
    print("=" * 60)

def test_specific_ticket(ticket_number):
    """Teste un ticket spécifique"""
    
    print(f"\n🔍 TEST DU TICKET: {ticket_number}")
    print("-" * 40)
    
    try:
        ticket = Ticket.objects.get(ticket_number=ticket_number)
        reservation = ticket.reservation
        now = timezone.now()
        
        print(f"✅ Ticket trouvé")
        print(f"   Statut: {'Utilisé' if ticket.is_used else 'Valide'}")
        print(f"   Réservation: {reservation}")
        print(f"   Début: {reservation.start_time}")
        print(f"   Fin: {reservation.end_time}")
        print(f"   Maintenant: {now}")
        
        # Test de validation
        if ticket.is_used:
            print("❌ Résultat: DÉJÀ UTILISÉ")
        elif reservation.start_time > now + timezone.timedelta(hours=2):
            print("❌ Résultat: TROP FUTURE")
        elif reservation.end_time < now:
            print("❌ Résultat: EXPIRÉE")
        else:
            print("✅ Résultat: VALIDE POUR SCAN")
        
    except Ticket.DoesNotExist:
        print(f"❌ Ticket {ticket_number} NON TROUVÉ")
        print("   Vérifiez le numéro ou créez le ticket")

if __name__ == "__main__":
    find_valid_tickets()
    
    # Test optionnel d'un ticket spécifique
    if len(sys.argv) > 1:
        test_specific_ticket(sys.argv[1])
