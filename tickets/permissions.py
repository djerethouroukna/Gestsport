# tickets/permissions.py
from rest_framework.permissions import BasePermission
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ExternalScannerPermission(BasePermission):
    """
    Permission personnalisée pour les scanners externes
    """
    
    def has_permission(self, request, view):
        """
        Vérifie si la requête vient d'un scanner externe autorisé
        """
        # Méthodes autorisées pour les scanners externes
        allowed_methods = ['GET', 'POST']
        if request.method not in allowed_methods:
            logger.warning(f"Méthode non autorisée: {request.method}")
            return False
        
        # Vérifier l'en-tête d'authentification du scanner
        scanner_key = request.META.get('HTTP_X_SCANNER_KEY')
        allowed_scanner_keys = getattr(settings, 'EXTERNAL_SCANNER_KEYS', ['SCANNER_2024_DEFAULT'])
        
        if not scanner_key:
            logger.warning("Requête sans clé de scanner")
            return False
        
        if scanner_key not in allowed_scanner_keys:
            logger.warning(f"Clé de scanner non valide: {scanner_key}")
            return False
        
        logger.info(f"Scanner autorisé: {scanner_key}")
        return True


class AllowExternalAPI(BasePermission):
    """
    Permission pour autoriser les appels API externes
    (désactive l'authentification Django standard)
    """
    
    def has_permission(self, request, view):
        """
        Autorise les appels API externes sans authentification Django
        """
        # Vérifier si c'est une route API externe
        if hasattr(view, '__module__') and 'api_external' in view.__module__:
            return True
        
        return False


def log_external_request(request, view_name):
    """
    Fonction utilitaire pour logger les requêtes externes
    """
    logger.info(f"API Externe - {view_name}")
    logger.info(f"Method: {request.method}")
    logger.info(f"IP: {get_client_ip(request)}")
    logger.info(f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    logger.info(f"Scanner Key: {request.META.get('HTTP_X_SCANNER_KEY', 'None')}")
    
    # Logger les paramètres
    if request.method == 'GET':
        logger.info(f"GET params: {dict(request.GET)}")
    elif request.method == 'POST':
        logger.info(f"POST body: {request.body}")


def get_client_ip(request):
    """
    Extraire l'IP réelle du client
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class ExternalAPIRateLimit:
    """
    Gestionnaire de rate limiting pour API externes
    """
    
    def __init__(self):
        self.requests = {}
        self.max_requests_per_minute = 60
        self.max_requests_per_hour = 1000
    
    def is_allowed(self, client_ip):
        """
        Vérifie si le client peut faire une requête
        """
        import time
        
        current_time = time.time()
        
        # Nettoyer les anciennes entrées
        self._cleanup_old_requests(current_time)
        
        # Vérifier le nombre de requêtes par minute
        minute_key = f"{client_ip}_{int(current_time // 60)}"
        minute_count = self.requests.get(minute_key, 0)
        
        if minute_count >= self.max_requests_per_minute:
            logger.warning(f"Rate limit dépassé pour {client_ip} (minute)")
            return False
        
        # Vérifier le nombre de requêtes par heure
        hour_key = f"{client_ip}_{int(current_time // 3600)}"
        hour_count = self.requests.get(hour_key, 0)
        
        if hour_count >= self.max_requests_per_hour:
            logger.warning(f"Rate limit dépassé pour {client_ip} (hour)")
            return False
        
        # Incrémenter les compteurs
        self.requests[minute_key] = minute_count + 1
        self.requests[hour_key] = hour_count + 1
        
        return True
    
    def _cleanup_old_requests(self, current_time):
        """
        Nettoie les entrées anciennes
        """
        cutoff_minute = int(current_time // 60) - 5  # Garder 5 minutes
        cutoff_hour = int(current_time // 3600) - 1  # Garder 1 heure
        
        keys_to_remove = []
        for key in self.requests.keys():
            if '_minute_' in key and int(key.split('_')[-1]) < cutoff_minute:
                keys_to_remove.append(key)
            elif '_hour_' in key and int(key.split('_')[-1]) < cutoff_hour:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.requests[key]


# Instance globale du rate limiter
rate_limiter = ExternalAPIRateLimit()
