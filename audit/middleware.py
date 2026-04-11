from django.utils.deprecation import MiddlewareMixin
import threading

# Stockage thread-local pour le contexte
_thread_local = threading.local()

class AuditMiddleware(MiddlewareMixin):
    """
    Middleware pour capturer les informations de requête
    et les rendre disponibles pour les signaux d'audit
    """
    
    def process_request(self, request):
        """Capture les informations de la requête"""
        # Stocker l'IP et le User-Agent dans la requête
        request.audit_ip = self.get_client_ip(request)
        request.audit_user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Stocker l'utilisateur courant dans le thread-local
        if hasattr(request, 'user') and request.user.is_authenticated:
            _thread_local.audit_user = request.user
            request.audit_user = request.user
        else:
            _thread_local.audit_user = None
            request.audit_user = None
        
        # Stocker l'IP et User-Agent dans le thread-local
        _thread_local.audit_ip = request.audit_ip
        _thread_local.audit_user_agent = request.audit_user_agent
        
        # Stocker des informations supplémentaires
        _thread_local.request_path = request.path
        _thread_local.request_method = request.method
        _thread_local.request_get = dict(request.GET)
        
        return None
    
    def process_response(self, request, response):
        """Nettoyer le thread-local après la réponse"""
        # Nettoyer les variables thread-local
        for attr in ['audit_user', 'audit_ip', 'audit_user_agent', 
                     'request_path', 'request_method', 'request_get']:
            if hasattr(_thread_local, attr):
                delattr(_thread_local, attr)
        
        return response
    
    def get_client_ip(self, request):
        """Extraire l'IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or None


def get_current_user():
    """Fonction utilitaire pour récupérer l'utilisateur courant"""
    return getattr(_thread_local, 'audit_user', None)


def get_current_ip():
    """Fonction utilitaire pour récupérer l'IP courante"""
    return getattr(_thread_local, 'audit_ip', None)


def get_current_user_agent():
    """Fonction utilitaire pour récupérer le User-Agent courant"""
    return getattr(_thread_local, 'audit_user_agent', '')


def get_request_context():
    """Fonction utilitaire pour récupérer le contexte de la requête"""
    return {
        'path': getattr(_thread_local, 'request_path', ''),
        'method': getattr(_thread_local, 'request_method', ''),
        'get_params': getattr(_thread_local, 'request_get', {})
    }
