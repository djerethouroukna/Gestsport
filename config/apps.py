from django.apps import AppConfig

class Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'
    
    def ready(self):
        """Importer les signaux quand l'app est prête"""
        import notifications.signals
