from django.core.management.base import BaseCommand
from django.db import connection
from users.models import User
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Nettoie les utilisateurs de test audit avec SQL brut (contourne les signaux)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simuler la suppression sans exécuter',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forcer la suppression sans confirmation',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('🔧 Nettoyage SQL des utilisateurs de test audit'))
        self.stdout.write('=' * 60)
        
        # Trouver les utilisateurs de test audit
        audit_users = User.objects.filter(email__contains='audit')
        
        if not audit_users.exists():
            self.stdout.write(self.style.WARNING('❌ Aucun utilisateur de test audit trouvé'))
            return
        
        self.stdout.write(f'📊 {audit_users.count()} utilisateur(s) de test audit trouvé(s):')
        
        for user in audit_users:
            self.stdout.write(f'   - ID: {user.id} | Email: {user.email}')
        
        if not force and not dry_run:
            confirm = input('\n⚠️  Voulez-vous continuer la suppression? (oui/non): ')
            if confirm.lower() != 'oui':
                self.stdout.write(self.style.WARNING('❌ Opération annulée'))
                return
        
        # Traiter chaque utilisateur avec SQL brut
        for user in audit_users:
            self.stdout.write(f'\n🔄 Traitement SQL de: {user.email} (ID: {user.id})')
            
            try:
                with connection.cursor() as cursor:
                    user_id = user.id
                    
                    if dry_run:
                        self.stdout.write(f'   🧪 [DRY RUN] Suppression SQL simulée')
                        continue
                    
                    # 1. Compter avant suppression
                    cursor.execute("""
                        SELECT 
                            COUNT(DISTINCT r.id) as reservations,
                            COUNT(DISTINCT t.id) as tickets,
                            COUNT(DISTINCT p.id) as payments,
                            COUNT(DISTINCT a.id) as audit_logs
                        FROM users_user u
                        LEFT JOIN reservations_reservation r ON u.id = r.user_id
                        LEFT JOIN tickets_ticket t ON r.id = t.reservation_id
                        LEFT JOIN payments_payment p ON r.id = p.reservation_id
                        LEFT JOIN audit_auditlog a ON u.id = a.user_id
                        WHERE u.id = %s
                    """, [user_id])
                    
                    counts = cursor.fetchone()
                    self.stdout.write(f'   📋 Réservations: {counts[0]}')
                    self.stdout.write(f'   🎫 Tickets: {counts[1]}')
                    self.stdout.write(f'   💳 Paiements: {counts[2]}')
                    self.stdout.write(f'   📋 Logs d\'audit: {counts[3]}')
                    
                    # 2. Supprimer dans l'ordre inverse des contraintes avec SQL
                    self.stdout.write(f'   🔧 Suppression avec SQL brut...')
                    
                    # Supprimer les logs d'audit
                    cursor.execute("DELETE FROM audit_auditlog WHERE user_id = %s", [user_id])
                    self.stdout.write(f'   ✅ Logs d\'audit supprimés')
                    
                    # Supprimer les tickets (via réservations)
                    cursor.execute("""
                        DELETE FROM tickets_ticket 
                        WHERE reservation_id IN (
                            SELECT id FROM reservations_reservation WHERE user_id = %s
                        )
                    """, [user_id])
                    self.stdout.write(f'   ✅ Tickets supprimés')
                    
                    # Supprimer les paiements (via réservations)
                    cursor.execute("""
                        DELETE FROM payments_payment 
                        WHERE reservation_id IN (
                            SELECT id FROM reservations_reservation WHERE user_id = %s
                        )
                    """, [user_id])
                    self.stdout.write(f'   ✅ Paiements supprimés')
                    
                    # Supprimer les réservations
                    cursor.execute("DELETE FROM reservations_reservation WHERE user_id = %s", [user_id])
                    self.stdout.write(f'   ✅ Réservations supprimées')
                    
                    # Supprimer les notifications
                    cursor.execute("DELETE FROM notifications_notification WHERE recipient_id = %s", [user_id])
                    self.stdout.write(f'   ✅ Notifications supprimées')
                    
                    # Supprimer les tokens d'authentification
                    cursor.execute("DELETE FROM authtoken_token WHERE user_id = %s", [user_id])
                    self.stdout.write(f'   ✅ Tokens d\'authentification supprimés')
                    
                    # Supprimer les préférences utilisateur
                    cursor.execute("DELETE FROM users_userpreferences WHERE user_id = %s", [user_id])
                    self.stdout.write(f'   ✅ Préférences supprimées')
                    
                    # Supprimer l'utilisateur
                    cursor.execute("DELETE FROM users_user WHERE id = %s", [user_id])
                    self.stdout.write(self.style.SUCCESS(f'   ✅ Utilisateur {user.email} supprimé'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Erreur SQL: {str(e)}'))
                logger.error(f'Erreur suppression SQL utilisateur {user.id}: {e}')
                # Annuler les changements en cas d'erreur
                connection.rollback()
                continue
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Nettoyage SQL terminé!'))
