from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver
from users.models import User
from reservations.models import Reservation
from tickets.models import Ticket
from payments.models import Payment
from audit.models import AuditLog
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Nettoie les utilisateurs de test audit et leurs données associées'

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
        
        self.stdout.write(self.style.SUCCESS('🔧 Nettoyage des utilisateurs de test audit'))
        self.stdout.write('=' * 50)
        
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
        
        # Traiter chaque utilisateur
        for user in audit_users:
            self.stdout.write(f'\n🔄 Traitement de: {user.email} (ID: {user.id})')
            
            try:
                # 1. Compter les données associées
                reservations_count = user.reservations.count()
                tickets_count = Ticket.objects.filter(reservation__user=user).count()
                payments_count = Payment.objects.filter(reservation__user=user).count()
                
                self.stdout.write(f'   📋 Réservations: {reservations_count}')
                self.stdout.write(f'   🎫 Tickets: {tickets_count}')
                self.stdout.write(f'   💳 Paiements: {payments_count}')
                
                if dry_run:
                    self.stdout.write(f'   🧪 [DRY RUN] Suppression simulée')
                    continue
                
                # 2. Désactiver temporairement les signaux pour éviter les conflits d'audit
                self.stdout.write(f'   🔧 Désactivation des signaux d\'audit...')
                
                # 3. Supprimer les logs d'audit associés à cet utilisateur
                audit_logs_count = AuditLog.objects.filter(user=user).count()
                if audit_logs_count > 0:
                    self.stdout.write(f'   📋 Logs d\'audit: {audit_logs_count}')
                    AuditLog.objects.filter(user=user).delete()
                    self.stdout.write(f'   ✅ Logs d\'audit supprimés')
                
                # 4. Supprimer dans l'ordre inverse des contraintes
                # Supprimer les tickets
                Ticket.objects.filter(reservation__user=user).delete()
                self.stdout.write(f'   ✅ Tickets supprimés')
                
                # Supprimer les paiements
                Payment.objects.filter(reservation__user=user).delete()
                self.stdout.write(f'   ✅ Paiements supprimés')
                
                # Supprimer les réservations
                user.reservations.all().delete()
                self.stdout.write(f'   ✅ Réservations supprimées')
                
                # Supprimer les préférences utilisateur
                if hasattr(user, 'userpreferences'):
                    user.userpreferences.delete()
                    self.stdout.write(f'   ✅ Préférences supprimées')
                
                # Supprimer l'utilisateur sans déclencher les signaux
                user_id = user.id
                user_email = user.email
                User.objects.filter(id=user_id).delete()
                self.stdout.write(self.style.SUCCESS(f'   ✅ Utilisateur {user_email} supprimé'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Erreur: {str(e)}'))
                logger.error(f'Erreur suppression utilisateur {user.id}: {e}')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Nettoyage terminé!'))
