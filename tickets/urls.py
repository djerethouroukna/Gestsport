# tickets/urls.py
from django.urls import path
from . import views
from . import api_external
from . import api_views

app_name = 'tickets'

urlpatterns = [
    # Génération et téléchargement
    path('generate/<int:reservation_id>/', views.generate_ticket, name='generate'),
    path('download/<int:reservation_id>/', views.download_ticket, name='download'),
    
    # Scan interne
    path('scan/', views.scan_ticket_view, name='scan'),
    path('api/scan/', views.scan_ticket_api, name='api_scan'),
    path('api/history/', views.scan_history, name='api_history'),
    
    # Documentation API
    path('api/docs/', views.api_documentation, name='api_docs'),
    
    # API REST pour vérification QR code
    path('api/verify/<str:ticket_number>/', api_views.verify_ticket_qr, name='api_verify'),
    path('api/validate/<str:ticket_number>/', api_views.validate_ticket, name='api_validate'),
    path('api/info/<str:ticket_number>/', api_views.ticket_info, name='api_info'),
    
    # API pour scanners externes
    path('api/scanner/scan/', api_views.scan_ticket_api, name='scanner_scan'),
    path('api/scanner/status/', api_views.scanner_status, name='scanner_status'),
    path('api/scanner/history/', api_views.scan_history, name='scanner_history'),
    
    # API externe pour système de scan
    path('api/external/ticket/validate/', api_external.external_ticket_validation, name='external_validate'),
    path('api/external/ticket/info/', api_external.external_ticket_info, name='external_info'),
    path('api/external/status/', api_external.external_system_status, name='external_status'),
]
