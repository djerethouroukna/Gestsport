# reservations/views_coach.py - Vues spécifiques pour les coachs
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
import logging

from .models import Reservation, ReservationStatus
from terrains.models import Terrain

logger = logging.getLogger(__name__)


def is_coach(user):
    """Vérifie si l'utilisateur est un coach"""
    return user.is_authenticated and user.role == 'coach'


class CoachRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur est un coach"""
    
    def test_func(self):
        return is_coach(self.request.user)
    
    def handle_no_permission(self):
        """Redirige vers le dashboard coach si non autorisé"""
        if self.request.user.is_authenticated:
            return redirect('dashboard_coach')
        return redirect('login')


@login_required
def coach_reservation_dashboard(request):
    """Dashboard coach avec ses réservations uniquement"""
    
    # Vérifier que l'utilisateur est un coach
    if not is_coach(request.user):
        return redirect('dashboard_coach')
    
    # Statistiques des réservations du coach
    my_reservations = Reservation.objects.filter(user=request.user)
    
    total_reservations = my_reservations.count()
    confirmed_reservations = my_reservations.filter(status='confirmed').count()
    pending_reservations = my_reservations.filter(status='pending').count()
    completed_reservations = my_reservations.filter(status='completed').count()
    
    # Réservations à venir
    upcoming_reservations = my_reservations.filter(
        start_time__gt=timezone.now(),
        status='confirmed'
    ).order_by('start_time')[:5]
    
    # Réservations récentes
    recent_reservations = my_reservations.order_by('-created_at')[:10]
    
    # Réservations par terrain
    reservations_by_terrain = my_reservations.values('terrain__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Réservations par statut
    reservations_by_status = my_reservations.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'total_reservations': total_reservations,
        'confirmed_reservations': confirmed_reservations,
        'pending_reservations': pending_reservations,
        'completed_reservations': completed_reservations,
        'upcoming_reservations': upcoming_reservations,
        'recent_reservations': recent_reservations,
        'reservations_by_terrain': reservations_by_terrain,
        'reservations_by_status': reservations_by_status,
        'is_coach_dashboard': True,
    }
    
    return render(request, 'reservations/coach_dashboard.html', context)


class CoachReservationListView(CoachRequiredMixin, ListView):
    """Liste des réservations du coach"""
    model = Reservation
    template_name = 'reservations/coach_reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 20
    
    def get_queryset(self):
        """Uniquement les réservations du coach"""
        queryset = Reservation.objects.filter(
            user=self.request.user
        ).select_related('terrain', 'ticket')
        
        # Appliquer les filtres
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        terrain_filter = self.request.GET.get('terrain')
        if terrain_filter:
            queryset = queryset.filter(terrain_id=terrain_filter)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(start_time__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(start_time__date__lte=date_to)
        
        return queryset.order_by('-start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['terrains'] = Terrain.objects.all()
        context['is_coach_view'] = True
        return context


class CoachReservationDetailView(CoachRequiredMixin, DetailView):
    """Détails d'une réservation du coach"""
    model = Reservation
    template_name = 'reservations/coach_reservation_detail.html'
    context_object_name = 'reservation'
    
    def get_queryset(self):
        """Uniquement les réservations du coach"""
        return Reservation.objects.filter(
            user=self.request.user
        ).select_related('user', 'terrain', 'ticket')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_coach_view'] = True
        return context


@login_required
@require_POST
@csrf_exempt
def coach_cancel_reservation(request, pk):
    """Annuler une réservation (coach uniquement)"""
    
    # Vérifier que l'utilisateur est un coach
    if not is_coach(request.user):
        return JsonResponse({
            'success': False,
            'error': 'Non autorisé'
        }, status=403)
    
    try:
        reservation = get_object_or_404(Reservation, pk=pk, user=request.user)
        
        # Vérifier que la réservation peut être annulée
        if reservation.status in ['completed', 'cancelled']:
            return JsonResponse({
                'success': False,
                'error': 'Cette réservation ne peut plus être annulée'
            })
        
        # Vérifier que c'est au moins 2 heures avant le début
        if reservation.start_time <= timezone.now() + timezone.timedelta(hours=2):
            return JsonResponse({
                'success': False,
                'error': 'Annulation impossible moins de 2h avant le début'
            })
        
        # Annuler la réservation
        reservation.status = ReservationStatus.CANCELLED
        reservation.save()
        
        logger.info(f"Réservation {pk} annulée par le coach {request.user.email}")
        
        return JsonResponse({
            'success': True,
            'message': 'Réservation annulée avec succès'
        })
        
    except Exception as e:
        logger.error(f"Erreur annulation réservation: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors de l\'annulation'
        }, status=500)


@login_required
def coach_reservation_stats(request):
    """Statistiques des réservations du coach en JSON"""
    
    # Vérifier que l'utilisateur est un coach
    if not is_coach(request.user):
        return JsonResponse({
            'success': False,
            'error': 'Non autorisé'
        }, status=403)
    
    try:
        my_reservations = Reservation.objects.filter(user=request.user)
        
        # Statistiques par mois
        monthly_stats = []
        for i in range(12):
            month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_start = month_start - timezone.timedelta(days=30*i)
            month_end = month_start + timezone.timedelta(days=30)
            
            month_reservations = my_reservations.filter(
                start_time__gte=month_start,
                start_time__lt=month_end
            ).count()
            
            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'count': month_reservations
            })
        
        return JsonResponse({
            'success': True,
            'monthly_stats': list(reversed(monthly_stats)),
            'total_reservations': my_reservations.count(),
            'confirmed_reservations': my_reservations.filter(status='confirmed').count(),
            'completed_reservations': my_reservations.filter(status='completed').count(),
            'cancelled_reservations': my_reservations.filter(status='cancelled').count(),
        })
        
    except Exception as e:
        logger.error(f"Erreur statistiques coach: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors du chargement des statistiques'
        }, status=500)
