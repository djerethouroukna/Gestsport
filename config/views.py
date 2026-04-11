# config/views.py - Vues principales du site
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


def test_reservation_view(request):
    """
    Page de test pour le flux de réservation
    """
    return render(request, 'test_reservation.html')


def home_view(request):
    """
    Page d'accueil principale

    Redirige les utilisateurs authentifiés vers leur dashboard selon leur rôle.
    """
    # Si l'utilisateur est authentifié, rediriger vers le dashboard approprié
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('dashboard_admin')
        elif request.user.role == 'coach':
            return redirect('dashboard_coach')
        elif request.user.role == 'player':
            return redirect('dashboard_player')
        else:
            return render(request, 'home_new.html')
    else:
        return render(request, 'home_public.html')


@login_required
def dashboard_admin_view(request):
    """
    Tableau de bord administrateur
    """
    # Statistiques rapides pour l'admin
    from reservations.models import Reservation
    from terrains.models import Terrain, TerrainStatus
    from django.contrib.auth import get_user_model
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    User = get_user_model()
    
    # Statistiques de base
    context = {
        'total_reservations': Reservation.objects.count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
        'total_terrains': Terrain.objects.count(),
        'total_users': User.objects.count(),
        'admin_count': User.objects.filter(role='admin').count(),
        'coach_count': User.objects.filter(role='coach').count(),
        'player_count': User.objects.filter(role='player').count(),
        'recent_users': User.objects.order_by('-date_joined')[:5],
        'recent_reservations': Reservation.objects.select_related('user', 'terrain').order_by('-created_at')[:5]
    }
    
    # Données pour les graphiques
    # Évolution des réservations (12 derniers mois)
    reservations_by_month = []
    month_labels = []
    for i in range(12):
        month_start = timezone.now().replace(day=1) - timedelta(days=i*30)
        month_end = month_start + timedelta(days=30)
        count = Reservation.objects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        reservations_by_month.append(count)
        month_labels.append(month_start.strftime('%B %Y'))  # Nom complet du mois en français
    
    context['reservations_chart_data'] = list(reversed(reservations_by_month))
    context['month_labels'] = list(reversed(month_labels))  # Ordre chronologique: janvier à décembre
    # Formatage des variables pour JavaScript
    import json
    print("DEBUG: month_labels =", month_labels)  # Debug
    print("DEBUG: reservations_by_month =", reservations_by_month)  # Debug
    
    context['reservations_chart_data'] = reservations_by_month  # Garder l'ordre naturel (janvier à décembre)
    context['month_labels'] = month_labels  # Garder l'ordre naturel (janvier à décembre)
    
    # Formatage des variables pour JavaScript - Labels vides pour masquer les mois
    empty_labels = [''] * len(month_labels)  # Créer une liste vide de la même longueur
    context['month_labels_json'] = json.dumps(empty_labels)
    context['reservations_chart_data_json'] = json.dumps(reservations_by_month)
    return render(request, 'dashboard/admin_new.html', context)

@login_required
def debug_chart_view(request):
    """Page de debug pour tester les variables Chart.js"""
    # Statistiques rapides pour l'admin
    from reservations.models import Reservation
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    # Données pour les graphiques (12 derniers mois)
    reservations_by_month = []
    month_labels = []
    for i in range(12):
        month_start = timezone.now().replace(day=1) - timedelta(days=i*30)
        month_end = month_start + timedelta(days=30)
        count = Reservation.objects.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        reservations_by_month.append(count)
        month_labels.append(month_start.strftime('%B %Y'))  # Nom complet du mois
    
    import json
    context = {
        'month_labels': month_labels,
        'reservations_by_month': reservations_by_month,
        'month_labels_json': json.dumps(list(reversed(month_labels))),
        'reservations_chart_data_json': json.dumps(list(reversed(reservations_by_month)))
    }
    
    return render(request, 'dashboard/debug_chart.html', context)


@login_required
def debug_session_view(request):
    """Page de debug pour analyser la session et les permissions"""
    user = request.user
    
    html = f"""
    <h1>DEBUG SESSION ET PERMISSIONS</h1>
    
    <h2>Informations Utilisateur</h2>
    <p><strong>Email:</strong> {user.email}</p>
    <p><strong>Rôle:</strong> {user.role}</p>
    <p><strong>is_staff:</strong> {user.is_staff}</p>
    <p><strong>is_superuser:</strong> {user.is_superuser}</p>
    <p><strong>is_active:</strong> {user.is_active}</p>
    <p><strong>is_authenticated:</strong> {user.is_authenticated}</p>
    
    <h2>Informations Session</h2>
    <p><strong>Session Key:</strong> {request.session.session_key}</p>
    <p><strong>Session Data:</strong></p>
    <pre>{dict(request.session)}</pre>
    
    <h2>Test de Permissions</h2>
    """
    
    # Tester les permissions pour différentes URLs
    test_urls = [
        ('Dashboard Coach', '/dashboard/coach/'),
        ('Réservations Standard', '/reservations/'),
        ('Dashboard Réservations Admin', '/reservations/admin/dashboard/'),
        ('Admin Django', '/admin/'),
    ]
    
    for name, url in test_urls:
        try:
            from django.urls import reverse
            if url.startswith('/admin/') and not url.startswith('/admin/'):
                # URL admin Django
                html += f"<p><strong>{name}:</strong> <a href='{url}' target='_blank'>{url}</a> (Admin Django)</p>"
            else:
                # URL de l'application
                url_name = None
                if url == '/dashboard/coach/':
                    url_name = 'dashboard_coach'
                elif url == '/reservations/':
                    url_name = 'reservations:reservation_list'
                elif url == '/reservations/admin/dashboard/':
                    url_name = 'reservations:admin_dashboard'
                
                if url_name:
                    try:
                        resolved_url = reverse(url_name)
                        html += f"<p><strong>{name}:</strong> <a href='{url}' target='_blank'>{url}</a> -> {resolved_url}</p>"
                    except Exception as e:
                        html += f"<p><strong>{name}:</strong> <a href='{url}' target='_blank'>{url}</a> -> ERREUR: {e}</p>"
                else:
                    html += f"<p><strong>{name}:</strong> <a href='{url}' target='_blank'>{url}</a></p>"
        except Exception as e:
            html += f"<p><strong>{name}:</strong> ERREUR: {e}</p>"
    
    html += """
    <h2>Actions</h2>
    <p><a href="/logout/">Se déconnecter</a></p>
    <p><a href="/dashboard/coach/">Dashboard Coach</a></p>
    <p><a href="/reservations/">Réservations</a></p>
    <p><a href="/reservations/admin/dashboard/">Dashboard Réservations</a></p>
    
    <script>
    // Log automatique des redirections
    window.addEventListener('beforeunload', function(e) {
        console.log('Page unload detected');
    });
    
    // Intercepter les clics sur les liens
    document.addEventListener('click', function(e) {
        if (e.target.tagName === 'A' && e.target.href) {
            console.log('Click detected:', e.target.href);
        }
    });
    </script>
    """
    
    from django.http import HttpResponse
    return HttpResponse(html)


@login_required
def coach_reservations_redirect(request):
    """Route directe pour les coachs vers leurs réservations"""
    if request.user.role == 'coach':
        return redirect('reservations:reservation_list')
    else:
        return redirect('dashboard_coach')


@login_required
def dashboard_coach_view(request):
    """
    Tableau de bord coach
    """
    from reservations.models import Reservation
    from terrains.models import Terrain
    from django.db.models import Count, Avg
    from django.utils import timezone
    from datetime import timedelta
    
    # Récupérer les réservations du coach
    my_reservations = Reservation.objects.filter(
        user=request.user
    ).select_related('terrain').order_by('-start_time')
    
    # Calculer la durée moyenne manuellement
    from django.db.models import ExpressionWrapper, F, DurationField
    from django.db.models.functions import Coalesce
    
    # Statistiques pour le coach
    # Calculer le taux de réservation (confirmées / total)
    total_reservations_count = Reservation.objects.filter(user=request.user).count()
    confirmed_reservations_count = Reservation.objects.filter(
        user=request.user,
        status='confirmed'
    ).count()
    reservation_rate = round((confirmed_reservations_count / total_reservations_count * 100), 1) if total_reservations_count > 0 else 0
    
    # Calculer la présence ce mois (réservations ce mois / jours du mois)
    from datetime import date
    today = date.today()
    days_in_month = (date(today.year, today.month % 12 + 1, 1) - date(today.year, today.month, 1)).days
    month_reservations = Reservation.objects.filter(
        user=request.user,
        start_time__month=today.month,
        start_time__year=today.year,
        status='confirmed'
    ).count()
    presence_rate = min(100, round((month_reservations / days_in_month * 100), 1)) if days_in_month > 0 else 0
    
    # Calculer la satisfaction (basée sur les réservations confirmées vs annulées)
    cancelled_reservations = Reservation.objects.filter(
        user=request.user,
        status='cancelled'
    ).count()
    total_processed = confirmed_reservations_count + cancelled_reservations
    satisfaction_score = round((confirmed_reservations_count / total_processed * 5), 1) if total_processed > 0 else 5.0
    
    context = {
        'my_reservations': my_reservations[:10],
        'pending_count': Reservation.objects.filter(
            user=request.user,
            status='pending'
        ).count(),
        'confirmed_count': Reservation.objects.filter(
            user=request.user,
            status='confirmed'
        ).count(),
        'total_reservations': total_reservations_count,
        # Nouvelles statistiques réelles
        'favorite_terrains': Reservation.objects.filter(
            user=request.user
        ).values('terrain').annotate(
            reservation_count=Count('id')
        ).order_by('-reservation_count')[:3].count(),
        'total_activities': 12,  # À adapter avec vos modèles d'activités
        'today_reservations': Reservation.objects.filter(
            user=request.user,
            start_time__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0),
            start_time__lt=timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        ).count(),
        'this_month_reservations': Reservation.objects.filter(
            user=request.user,
            start_time__gte=timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).count(),
        # Calculer la durée moyenne sans utiliser le champ 'duration' qui n'existe pas
        'avg_reservation_duration': 60,  # Valeur par défaut en minutes
        
        # Nouvelles métriques de performance
        'reservation_rate': reservation_rate,
        'presence_rate': presence_rate,
        'satisfaction_score': satisfaction_score,
        'satisfaction_percentage': min(round(satisfaction_score * 20), 100),
    }
    
    return render(request, 'dashboard/coach_new.html', context)


@login_required
def dashboard_player_view(request):
    """
    Tableau de bord joueur
    """
    from reservations.models import Reservation
    from subscriptions.models import Subscription, UserCredit
    
    context = {
        'my_reservations': Reservation.objects.filter(
            user=request.user
        ).select_related('terrain').order_by('-start_time')[:5],
        'active_subscription': Subscription.objects.filter(
            user=request.user,
            status='active',
            end_date__gt=timezone.now()
        ).first(),
        'available_credits': UserCredit.objects.filter(
            user=request.user,
            is_active=True,
            amount__gt=0
        ).order_by('expires_at')
    }
    
    return render(request, 'dashboard/player_new.html', context)


def about_view(request):
    """
    Page à propos
    """
    return render(request, 'about.html')


def contact_view(request):
    """
    Page de contact
    """
    # Si l'utilisateur est authentifié, utiliser le dashboard design
    if request.user.is_authenticated:
        return render(request, 'contact_dashboard.html')
    else:
        return render(request, 'contact.html')


class ScannerAPIView(APIView):
    """
    API pour le scanner de tickets GestSport
    """
    
    def post(self, request):
        """
        Valide un ticket via scan
        """
        try:
            # Récupérer les données
            qr_data = request.data.get('qr_data', '').strip()
            scanner_id = request.data.get('scanner_id', '').strip()
            location = request.data.get('location', '').strip()
            
            # Nettoyer le QR data (enlever "ticket_" si présent)
            if qr_data.startswith('ticket_'):
                qr_data = qr_data.replace('ticket_', '')
            
            # Validation des entrées
            if not qr_data:
                return Response({
                    'success': False,
                    'message': 'QR data requis',
                    'error_code': 'MISSING_QR_DATA'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not scanner_id:
                return Response({
                    'success': False,
                    'message': 'Scanner ID requis',
                    'error_code': 'MISSING_SCANNER_ID'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Importer ici pour éviter les imports circulaires
            from tickets.models import Ticket, Scan
            
            # Rechercher le ticket
            try:
                ticket = Ticket.objects.get(ticket_number=qr_data)
            except Ticket.DoesNotExist:
                logger.warning(f"Ticket non trouvé: {qr_data} par scanner {scanner_id}")
                return Response({
                    'success': False,
                    'message': 'Ticket non trouvé',
                    'error_code': 'TICKET_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Vérifier si le ticket est valide
            if ticket.is_used:
                logger.warning(f"Ticket déjà utilisé: {qr_data} par scanner {scanner_id}")
                return Response({
                    'success': False,
                    'message': 'Ticket déjà utilisé',
                    'error_code': 'TICKET_ALREADY_USED',
                    'used_at': ticket.used_at.isoformat() if ticket.used_at else None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier si la réservation est valide
            reservation = ticket.reservation
            from django.utils import timezone
            now = timezone.now()
            
            # Autoriser la validation jusqu'à 2 heures avant
            if reservation.start_time > now + timezone.timedelta(hours=2):
                logger.info(f"Réservation trop future: {qr_data} par scanner {scanner_id}")
                return Response({
                    'success': False,
                    'message': 'Réservation trop future (plus de 2h)',
                    'error_code': 'RESERVATION_TOO_FUTURE',
                    'start_time': reservation.start_time.isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if reservation.end_time < now:
                logger.warning(f"Réservation expirée: {qr_data} par scanner {scanner_id}")
                return Response({
                    'success': False,
                    'message': 'Réservation expirée',
                    'error_code': 'RESERVATION_EXPIRED',
                    'end_time': reservation.end_time.isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Valider le ticket
            with transaction.atomic():
                # Marquer le ticket comme utilisé
                ticket.is_used = True
                ticket.used_at = now
                # Note: used_by n'est pas disponible dans le modèle actuel
                ticket.save()
                
                # Enregistrer le scan
                scan = Scan.objects.create(
                    scanner_id=scanner_id,
                    ticket=ticket,
                    location=location or 'Non spécifié',
                    is_valid=True
                )
                
                logger.info(f"Ticket validé: {qr_data} par scanner {scanner_id} à {location}")
                
                return Response({
                    'success': True,
                    'message': 'Ticket validé avec succès',
                    'ticket_info': {
                        'ticket_number': ticket.ticket_number,
                        'reservation_id': reservation.id,
                        'activity': reservation.activity.title if reservation.activity else 'Réservation standard',
                        'terrain': reservation.terrain.name,
                        'user': reservation.user.get_full_name() or reservation.user.username,
                        'start_time': reservation.start_time.isoformat(),
                        'end_time': reservation.end_time.isoformat()
                    },
                    'scan_info': {
                        'scanner_id': scanner_id,
                        'location': location,
                        'scanned_at': scan.scanned_at.isoformat()
                    }
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Erreur scanner API: {e}")
            return Response({
                'success': False,
                'message': 'Erreur serveur',
                'error_code': 'SERVER_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        """
        Retourne le statut du scanner
        """
        try:
            scanner_id = request.GET.get('scanner_id', '').strip()
            
            if not scanner_id:
                return Response({
                    'success': False,
                    'message': 'Scanner ID requis',
                    'error_code': 'MISSING_SCANNER_ID'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from tickets.models import Scan
            from django.utils import timezone
            from datetime import datetime
            
            today = timezone.now().date()
            
            # Statistiques du scanner
            scans_today = Scan.objects.filter(
                scanner_id=scanner_id,
                scanned_at__date=today
            ).count()
            
            total_scans = Scan.objects.filter(scanner_id=scanner_id).count()
            
            # Scans récents
            recent_scans = Scan.objects.filter(
                scanner_id=scanner_id
            ).select_related('ticket__reservation__user', 'ticket__reservation__terrain').order_by('-scanned_at')[:5]
            
            recent_scans_data = []
            for scan in recent_scans:
                recent_scans_data.append({
                    'ticket_number': scan.ticket.ticket_number,
                    'user': scan.ticket.reservation.user.get_full_name() or scan.ticket.reservation.user.username,
                    'terrain': scan.ticket.reservation.terrain.name,
                    'scanned_at': scan.scanned_at.isoformat(),
                    'is_valid': scan.is_valid
                })
            
            return Response({
                'success': True,
                'status': 'active',
                'scanner_id': scanner_id,
                'scans_today': scans_today,
                'total_scans': total_scans,
                'recent_scans': recent_scans_data,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur statut scanner: {e}")
            return Response({
                'success': False,
                'message': 'Erreur serveur',
                'error_code': 'SERVER_ERROR',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
