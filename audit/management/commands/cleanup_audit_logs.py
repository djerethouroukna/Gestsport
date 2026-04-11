from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
import logging

from audit.models import AuditLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Nettoie les anciens logs d\'audit pour maintenir les performances'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Nombre de jours à conserver (défaut: 365)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simuler le nettoyage sans supprimer'
        )
        parser.add_argument(
            '--keep-actions',
            nargs='+',
            choices=['CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'FAILED_LOGIN'],
            help='Actions à conserver même si elles sont anciennes'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Taille des lots pour la suppression (défaut: 1000)'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        keep_actions = options['keep_actions']
        batch_size = options['batch_size']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            f'🧹 Nettoyage des logs d\'audit antérieurs à {cutoff_date.strftime("%d/%m/%Y")} '
            f'({days} jours)'
        )
        
        # Compter les logs à supprimer
        queryset = AuditLog.objects.filter(timestamp__lt=cutoff_date)
        
        if keep_actions:
            queryset = queryset.exclude(action__in=keep_actions)
            self.stdout.write(f'📋 Actions conservées: {", ".join(keep_actions)}')
        
        total_to_delete = queryset.count()
        
        if total_to_delete == 0:
            self.stdout.write('✅ Aucun log à supprimer')
            return
        
        self.stdout.write(f'📊 Logs à supprimer: {total_to_delete:,}')
        
        if dry_run:
            self.stdout.write('🔍 MODE SIMULATION - Aucune suppression réelle')
            return
        
        # Confirmation
        if not self.confirm_deletion(total_to_delete):
            self.stdout.write('❌ Opération annulée')
            return
        
        # Suppression par lots
        deleted_count = 0
        with transaction.atomic():
            while queryset.exists():
                batch = queryset[:batch_size]
                batch_count = batch.count()
                batch.delete()
                deleted_count += batch_count
                
                progress = (deleted_count / total_to_delete) * 100
                self.stdout.write(
                    f'⏳ Progression: {deleted_count:,}/{total_to_delete:,} '
                    f'({progress:.1f}%)'
                )
        
        # Statistiques finales
        remaining_logs = AuditLog.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Nettoyage terminé!\n'
                f'   • Logs supprimés: {deleted_count:,}\n'
                f'   • Logs restants: {remaining_logs:,}\n'
                f'   • Espace libéré: ~{deleted_count * 0.5:.1f} KB'
            )
        )
        
        # Alerte si beaucoup de suppressions
        if deleted_count > 10000:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️ Grand nombre de suppressions détecté. '
                    'Considérez réduire la période de rétention.'
                )
            )
    
    def confirm_deletion(self, count):
        """Demande confirmation à l'utilisateur"""
        self.stdout.write(
            f'\n⚠️ Vous êtes sur le point de supprimer {count:,} logs d\'audit.'
        )
        self.stdout.write('Cette action est IRREVERSIBLE.\n')
        
        response = input('Êtes-vous sûr de vouloir continuer? [oui/N]: ').strip().lower()
        return response in ['oui', 'yes', 'o', 'y']
