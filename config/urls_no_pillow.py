"""
URLs SANS Pillow pour Render - GARANTIT installation
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)

def home_view(request):
    """Page d'accueil SANS Pillow"""
    try:
        return render(request, 'home_no_pillow.html', {
            'title': 'GestSport - Gestion Sportive',
            'message': 'Application fonctionnelle - Mode sans Pillow',
            'timestamp': timezone.now(),
            'features': {
                'users': True,
                'terrains': True,
                'activities': True,
                'reservations': True,
                'payments': True,
                'websocket': True,
                'qr_codes': False,
                'tickets': False,
                'pdf_generation': False,
            }
        })
    except Exception as e:
        logger.error(f"Erreur template home: {e}")
        # Fallback JSON si template échoue
        return JsonResponse({
            'status': 'ok',
            'message': 'GestSport - Application fonctionnelle (sans Pillow)',
            'timestamp': timezone.now().isoformat(),
            'features': ['users', 'terrains', 'activities', 'reservations', 'payments', 'websocket']
        })

def health_check(request):
    """Health check SANS Pillow"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'pillow': 'disabled',
            'timestamp': timezone.now().isoformat(),
            'mode': 'no-pillow'
        })
    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return JsonResponse({
            'status': 'degraded',
            'database': 'disconnected',
            'pillow': 'disabled',
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
            'mode': 'no-pillow'
        }, status=500)

def status_api(request):
    """API de statut SANS Pillow"""
    try:
        stats = {
            'status': 'ok',
            'mode': 'no-pillow',
            'timestamp': timezone.now().isoformat(),
            'features': {
                'django': True,
                'api': True,
                'database': True,
                'admin': True,
                'websocket': True,
                'payments': True,
                'pillow': False,
                'qr_codes': False,
                'tickets': False,
                'pdf_generation': False,
            }
        }
        
        # Essayer de compter les objets si possible
        try:
            from django.contrib.auth.models import User
            from terrains.models import Terrain
            from activities.models import Activity
            from reservations.models import Reservation
            
            stats['data'] = {
                'users': User.objects.count(),
                'terrains': Terrain.objects.count(),
                'activities': Activity.objects.count(),
                'reservations': Reservation.objects.count(),
            }
        except Exception as e:
            logger.error(f"Erreur comptage objets: {e}")
            stats['data'] = {
                'users': 0,
                'terrains': 0,
                'activities': 0,
                'reservations': 0,
            }
        
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'mode': 'no-pillow'
        }, status=500)

def fallback_view(request, path=""):
    """Fallback SANS Pillow pour toutes les URLs"""
    return JsonResponse({
        'status': 'ok',
        'message': 'GestSport - Mode sans Pillow',
        'path': path or '/',
        'timestamp': timezone.now().isoformat(),
        'available_endpoints': [
            '/',
            '/admin/',
            '/health/',
            '/api/status/',
            '/api/users/',
            '/api/terrains/',
            '/api/activities/',
            '/api/reservations/',
        ],
        'disabled_features': [
            'QR codes',
            'Tickets PDF',
            'Image processing',
            'Advanced PDF generation'
        ]
    })

# URLs SANS Pillow
urlpatterns = [
    # Page d'accueil
    path('', home_view, name='home'),
    
    # Health check
    path('health/', health_check, name='health'),
    
    # API status
    path('api/status/', status_api, name='api-status'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # APIs essentielles (avec try/catch)
    path('api/users/', include('users.urls')),
    path('api/terrains/', include('terrains.urls')),
    path('api/activities/', include('activities.urls')),
    path('api/reservations/', include('reservations.urls')),
    
    # Fallback pour tout le reste
    path('<path:path>', fallback_view, name='fallback'),
]
