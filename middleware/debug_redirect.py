# middleware/debug_redirect.py - Middleware pour debugger les redirections
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class DebugRedirectMiddleware(MiddlewareMixin):
    """Middleware pour logger les redirections et aider au debug"""
    
    def process_response(self, request, response):
        # Logger les redirections
        if response.status_code == 302:
            user_info = "Anonymous"
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_info = f"{request.user.email} (role: {getattr(request.user, 'role', 'unknown')}, is_staff: {request.user.is_staff})"
            
            logger.warning(f"REDIRECTION DETECTÉE:")
            logger.warning(f"  User: {user_info}")
            logger.warning(f"  From: {request.get_full_path()}")
            logger.warning(f"  To: {response.get('Location', 'Unknown')}")
            logger.warning(f"  Status: {response.status_code}")
        
        return response
