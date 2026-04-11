# reservations/views_admin.py - Vues spécifiques pour l'admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
import logging

from .models import Reservation, ReservationStatus
from terrains.models import Terrain

logger = logging.getLogger(__name__)


@login_required
def admin_reservation_dashboard(request):
    """Dashboard admin avec statistiques et fonctionnalités avancées"""
    
    # Vérifier les permissions
    if request.user.role == 'admin':
        # Admin voit toutes les réservations
        reservations_queryset = Reservation.objects.all()
        is_admin = True
    elif request.user.role == 'coach':
        # Coach voit uniquement ses réservations
        reservations_queryset = Reservation.objects.filter(user=request.user)
        is_admin = False
    else:
        # Autres rôles non autorisés
        return redirect('dashboard_coach')
    
    # Statistiques
    total_reservations = reservations_queryset.count()
    print(f"DEBUG: total_reservations = {total_reservations}")
    
    confirmed_reservations = reservations_queryset.filter(status='completed').count()
    print(f"DEBUG: confirmed_reservations = {confirmed_reservations} (filter: status='completed')")
    
    expired_reservations = reservations_queryset.filter(
        end_time__lt=timezone.now(),
        status='completed'
    ).count()
    print(f"DEBUG: expired_reservations = {expired_reservations} (filter: end_time__lt=now, status='completed')")
    
    completed_today = reservations_queryset.filter(
        status='completed',
        end_time__date=timezone.now().date()
    ).count()
    print(f"DEBUG: completed_today = {completed_today} (filter: status='completed', end_time__date=today)")
    
    # Vérifier les statuts disponibles
    all_statuses = reservations_queryset.values_list('status', flat=True).distinct()
    print(f"DEBUG: statuts disponibles = {list(all_statuses)}")
    
    # Vérifier quelques réservations
    sample_reservations = reservations_queryset[:5]
    for res in sample_reservations:
        print(f"DEBUG: réservation exemple - status: {res.status}, end_time: {res.end_time}")
    
    # Pourcentages simples et clairs
    if total_reservations > 0:
        confirmed_percentage = (confirmed_reservations / total_reservations) * 100
        expired_percentage = (expired_reservations / total_reservations) * 100
        completed_today_percentage = (completed_today / total_reservations) * 100
    else:
        confirmed_percentage = expired_percentage = completed_today_percentage = 0
    
    # DEBUG: Afficher les valeurs calculées
    print(f"DEBUG admin_dashboard:")
    print(f"  total_reservations: {total_reservations}")
    print(f"  confirmed_reservations: {confirmed_reservations}")
    print(f"  expired_reservations: {expired_reservations}")
    print(f"  completed_today: {completed_today}")
    print(f"  confirmed_percentage: {confirmed_percentage}")
    print(f"  expired_percentage: {expired_percentage}")
    print(f"  completed_today_percentage: {completed_today_percentage}")
    
    # Réservations expirées récentes
    recent_expired = reservations_queryset.filter(
        end_time__lt=timezone.now(),
        status='confirmed'
    ).order_by('-end_time')[:10]
    
    # Réservations par terrain
    reservations_by_terrain = reservations_queryset.values('terrain__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Réservations par statut
    reservations_by_status = reservations_queryset.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'total_reservations': total_reservations,
        'confirmed_reservations': confirmed_reservations,
        'expired_reservations': expired_reservations,
        'completed_today': completed_today,
        'recent_expired': recent_expired,
        'reservations_by_terrain': reservations_by_terrain,
        'reservations_by_status': reservations_by_status,
        'terrains': Terrain.objects.all(),
        'is_admin_dashboard': is_admin,  # Pour différencier dans le template
        'is_coach_dashboard': not is_admin,
        # Pourcentages simples
        'confirmed_percentage': confirmed_percentage,
        'expired_percentage': expired_percentage,
        'completed_today_percentage': completed_today_percentage,
    }
    
    template_name = 'reservations/admin_dashboard.html'
    return render(request, template_name, context)


@login_required
def admin_reservation_list(request):
    """Liste des réservations pour l'admin avec toutes les fonctionnalités"""
    
    # Vérifier les permissions
    if request.user.role == 'admin':
        # Admin voit toutes les réservations
        queryset = Reservation.objects.select_related('terrain', 'user', 'ticket')
        is_admin = True
    elif request.user.role == 'coach':
        # Coach voit uniquement ses réservations
        queryset = Reservation.objects.filter(user=request.user).select_related('terrain', 'user', 'ticket')
        is_admin = False
    else:
        # Autres rôles non autorisés
        return redirect('dashboard_coach')
    
    # Appliquer les filtres
    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter == 'expired':
            # Filtre spécial pour les réservations expirées
            queryset = queryset.filter(
                end_time__lt=timezone.now(),
                status='confirmed'
            )
        else:
            queryset = queryset.filter(status=status_filter)
    
    terrain_filter = request.GET.get('terrain')
    if terrain_filter:
        queryset = queryset.filter(terrain_id=terrain_filter)
    
    date_from = request.GET.get('date_from')
    if date_from:
        queryset = queryset.filter(start_time__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        queryset = queryset.filter(start_time__date__lte=date_to)
    
    user_filter = request.GET.get('user')
    if user_filter and is_admin:
        # Seul l'admin peut filtrer par utilisateur
        queryset = queryset.filter(
            Q(user__email__icontains=user_filter) |
            Q(user__first_name__icontains=user_filter) |
            Q(user__last_name__icontains=user_filter)
        )
    
    # Trier
    queryset = queryset.order_by('-start_time')
    
    context = {
        'reservations': queryset,
        'terrains': Terrain.objects.all(),
        'is_admin_view': is_admin,
        'is_coach_view': not is_admin,
    }
    
    return render(request, 'reservations/admin_reservation_list.html', context)


@login_required
def admin_reservation_detail(request, pk):
    """Vue admin pour voir les détails d'une réservation"""
    
    # Vérifier les permissions
    if request.user.role == 'admin':
        # Admin peut voir toutes les réservations
        reservation = get_object_or_404(Reservation.objects.select_related('user', 'terrain', 'ticket'), pk=pk)
        is_admin = True
    elif request.user.role == 'coach':
        # Coach ne peut voir que ses réservations
        reservation = get_object_or_404(Reservation.objects.select_related('user', 'terrain', 'ticket'), pk=pk, user=request.user)
        is_admin = False
    else:
        # Autres rôles non autorisés
        return redirect('dashboard_coach')
    
    context = {
        'reservation': reservation,
        'is_admin_view': is_admin,
        'is_coach_view': not is_admin,
    }
    return render(request, 'reservations/admin_reservation_detail.html', context)


@login_required
@staff_member_required
def admin_reservation_edit(request, pk):
    """Vue admin pour modifier une réservation - redirige vers l'admin Django"""
    return redirect(f'/admin/reservations/reservation/{pk}/change/')


@login_required
@staff_member_required
@require_POST
@csrf_exempt
def run_expired_check(request):
    """Exécuter la vérification des réservations expirées depuis l'admin"""
    try:
        # Appeler la commande de gestion
        call_command('check_expired_reservations')
        
        # Compter les réservations mises à jour
        updated_count = Reservation.objects.filter(
            end_time__lt=timezone.now(),
            status=ReservationStatus.COMPLETED,
            updated_at__date=timezone.now().date()
        ).count()
        
        return JsonResponse({
            'success': True,
            'updated': updated_count,
            'message': f'{updated_count} réservations mises à jour'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des réservations expirées: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@staff_member_required
@require_POST
@csrf_exempt
def mark_expired_completed(request):
    """Marquer toutes les réservations expirées comme terminées"""
    try:
        # Mettre à jour toutes les réservations expirées
        updated_count = Reservation.objects.filter(
            end_time__lt=timezone.now(),
            status=ReservationStatus.CONFIRMED
        ).update(status=ReservationStatus.COMPLETED)
        
        return JsonResponse({
            'success': True,
            'updated': updated_count,
            'message': f'{updated_count} réservations marquées comme terminées'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du marquage des réservations expirées: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
