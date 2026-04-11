from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    verbose_name = 'Audit et Traçabilité'
    
    def ready(self):
        """Importer les signaux et le middleware quand l'app est prête"""
        import audit.signals
