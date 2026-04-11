"""
Health check endpoint pour Render
"""
from django.http import JsonResponse
from django.db import connection
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Health check endpoint pour Render
    """
    try:
        # Test de connexion à la base de données
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)
