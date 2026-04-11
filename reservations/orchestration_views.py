# reservations/orchestration_views.py - Vues Django avec services d'orchestration
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from django.http import JsonResponse, HttpResponseNotFound
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import transaction
from datetime import datetime
from decimal import Decimal

from .models import Reservation, ReservationStatus
from .services import ReservationOrchestrationService, TimeSlotService
from .analytics import ReservationAnalyticsService
from terrains.models import Terrain
from subscriptions.models import Subscription, UserCredit


class ReservationCreateOrchestratedView(LoginRequiredMixin, CreateView):
    """Vue de création de réservation avec orchestration complète"""
    model = Reservation
    template_name = 'reservations/reservation_create_orchestrated.html'
    fields = []  # On utilise un formulaire personnalisé, pas les champs du modèle
    success_url = reverse_lazy('reservations:reservation_list_orchestrated')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer tous les terrains
        context['terrains'] = Terrain.objects.filter(status='available')
        
        # Récupérer l'abonnement actif de l'utilisateur
        active_subscription = Subscription.objects.filter(
            user=self.request.user,
            status='active',
            end_date__gt=timezone.now()
        ).select_related('membership').first()
        
        context['active_subscription'] = active_subscription
        
        # Récupérer les crédits disponibles
        user_credits = UserCredit.objects.filter(
            user=self.request.user,
            is_active=True,
            amount__gt=0
        ).order_by('expires_at')
        
        total_credits = sum(credit.amount for credit in user_credits)
        context['available_credits'] = user_credits
        context['total_credits'] = total_credits
        
        return context
    
    def post(self, request, *args, **kwargs):
        terrain_id = request.POST.get('terrain_id')
        start_datetime = request.POST.get('start_datetime')
        end_datetime = request.POST.get('end_datetime')
        notes = request.POST.get('notes', '')
        use_subscription = 'use_subscription' in request.POST
        use_credits = 'use_credits' in request.POST
        
        if not all([terrain_id, start_datetime, end_datetime]):
            messages.error(request, 'Veuillez remplir tous les champs obligatoires')
            return self.get(request, *args, **kwargs)
        
        try:
            terrain = Terrain.objects.get(id=terrain_id)
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            
            # Utiliser le service d'orchestration
            result = ReservationOrchestrationService.create_complete_reservation(
                user=request.user,
                terrain=terrain,
                start_datetime=start_dt,
                end_datetime=end_dt,
                notes=notes,
                use_subscription=use_subscription,
                use_credits=use_credits
            )
            
            if result['success']:
                messages.success(request, 'Réservation créée avec succès!')
                return redirect(f"{reverse_lazy('reservations:reservation_list_orchestrated')}?reservation_created={result['reservation'].id}#confirmation")
            else:
                messages.error(request, f"Erreur: {result['error']}")
                if 'waiting_list' in result and result['waiting_list'].get('success'):
                    messages.info(request, "Vous avez été ajouté à la liste d'attente")
                
                return self.get(request, *args, **kwargs)
                
        except Terrain.DoesNotExist:
            messages.error(request, 'Terrain non trouvé')
        except Exception as e:
            messages.error(request, f'Erreur technique: {str(e)}')
        
        return self.get(request, *args, **kwargs)


class ReservationDetailOrchestratedView(LoginRequiredMixin, DetailView):
    """Vue de détail de réservation avec toutes les informations connectées"""
    model = Reservation
    template_name = 'reservations/reservation_detail_orchestrated.html'
    context_object_name = 'reservation'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Récupérer tous les détails via le service
        result = ReservationOrchestrationService.get_reservation_details(self.object.id)
        
        if result['success']:
            details = result['details']
            context.update({
                'timeslot': details['timeslot'],
                'payment': details['payment'],
                'price_history': details['price_history'],
                'subscription': details['subscription'],
                'user_credits': details['user_credits'],
                'waiting_list_entry': details['waiting_list_entry']
            })
        
        return context


class ReservationListViewOrchestrated(LoginRequiredMixin, ListView):
    """Vue liste avec analytics intégrés"""
    model = Reservation
    template_name = 'reservations/reservation_list_orchestrated.html'
    context_object_name = 'reservations'
    paginate_by = 12
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Vérifier s'il y a un message de confirmation
        if 'reservation_created' in self.request.GET:
            reservation_id = self.request.GET.get('reservation_created')
            try:
                reservation = Reservation.objects.get(id=reservation_id)
                context['confirmation_reservation'] = reservation
                context['confirmation_type'] = 'created'
                
                # Récupérer les détails complets via le service
                result = ReservationOrchestrationService.get_reservation_details(reservation_id)
                
                if result['success']:
                    details = result['details']
                    context.update({
                        'confirmation_payment': details['payment'],
                        'confirmation_price_history': details['price_history'],
                        'confirmation_subscription': details['subscription']
                    })
            except Reservation.DoesNotExist:
                pass
        
        # Vérifier s'il y a un message d'annulation
        if 'reservation_cancelled' in self.request.GET:
            reservation_id = self.request.GET.get('reservation_cancelled')
            try:
                reservation = Reservation.objects.get(id=reservation_id)
                context['confirmation_reservation'] = reservation
                context['confirmation_type'] = 'cancelled'
            except Reservation.DoesNotExist:
                pass
        
        # Ajouter les analytics de l'utilisateur
        user_analytics = ReservationAnalyticsService.get_user_analytics(self.request.user.id)
        context['user_analytics'] = user_analytics
        
        # Statistiques rapides
        context['total_reservations'] = self.get_queryset().count()
        context['active_reservations'] = self.get_queryset().filter(
            status__in=['pending', 'confirmed']
        ).count()
        
        return context
    
    def get_queryset(self):
        user = self.request.user
        queryset = Reservation.objects.select_related('terrain', 'user').prefetch_related('payment')
        
        if user.role == 'admin':
            return queryset
        else:
            return queryset.filter(user=user)


@login_required
def check_availability_view(request):
    """Vue AJAX pour vérifier la disponibilité et le prix"""
    if request.method == 'POST':
        terrain_id = request.POST.get('terrain_id')
        start_datetime = request.POST.get('start_datetime')
        end_datetime = request.POST.get('end_datetime')
        
        try:
            terrain = Terrain.objects.get(id=terrain_id)
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            
            # Vérification via le service (incluant activités)
            is_available, conflicts = TimeSlotService.check_availability(
                terrain, start_dt, end_dt
            )

            # Vérifier les activités conflictuelles
            from activities.models import Activity, ActivityStatus
            activity_conflicts = Activity.objects.filter(
                terrain=terrain,
                status=ActivityStatus.CONFIRMED,
                start_time__lt=end_dt,
                end_time__gt=start_dt
            )
            if activity_conflicts.exists():
                is_available = False
                # Ajouter les activités comme conflits
                for a in activity_conflicts:
                    conflicts.append(a)

            # Calcul du prix
            from pricing.services import DynamicPricingService
            pricing_result = DynamicPricingService.calculate_price(
                terrain=terrain,
                start_datetime=start_dt,
                end_datetime=end_dt,
                user=request.user
            )
            
            # Vérification abonnement/crédits
            from .services import SubscriptionService, CreditService
            subscription_result = SubscriptionService.get_best_subscription(request.user, terrain)
            credit_result = CreditService.use_available_credits(request.user, pricing_result['final_price'])
            
            # Sérialiser conflits (Timeslot, Activity, Block)
            serialized_conflicts = []
            for conflict in conflicts:
                if hasattr(conflict, 'title') and hasattr(conflict, 'start_time'):
                    # Activity
                    serialized_conflicts.append({
                        'type': 'activity',
                        'id': f'activity_{conflict.id}',
                        'title': conflict.title,
                        'terrain': conflict.terrain.name,
                        'start_time': conflict.start_time.isoformat(),
                        'end_time': conflict.end_time.isoformat(),
                        'status': conflict.status,
                        'coach': conflict.coach.get_full_name() if conflict.coach else None
                    })
                elif hasattr(conflict, 'start_time') and hasattr(conflict, 'date'):
                    # TimeSlot
                    serialized_conflicts.append({
                        'type': 'timeslot',
                        'id': str(conflict.id),
                        'terrain': conflict.terrain.name,
                        'date': conflict.date.isoformat(),
                        'start_time': conflict.start_time.isoformat(),
                        'end_time': conflict.end_time.isoformat(),
                        'status': conflict.status
                    })
                else:
                    # Fallback
                    try:
                        serialized_conflicts.append({'type': 'unknown', 'repr': str(conflict)})
                    except Exception:
                        serialized_conflicts.append({'type': 'unknown'})

            return JsonResponse({
                'success': True,
                'available': is_available,
                'conflicts': serialized_conflicts,
                'pricing': {
                    'base_price': float(pricing_result['base_price']),
                    'final_price': float(pricing_result['final_price']),
                    'total_discount': float(pricing_result['total_discount']),
                    'applied_rules': pricing_result['applied_rules']
                },
                'subscription': {
                    'available': subscription_result['success'],
                    'discount': float(subscription_result['discount']) if subscription_result['success'] else 0,
                    'name': subscription_result['subscription'].membership.name if subscription_result['success'] else None
                },
                'credits': {
                    'available': credit_result['success'],
                    'total_available': float(credit_result['available']) if not credit_result['success'] else 0
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
def cancel_reservation_view(request, reservation_id):
    """Vue pour annuler une réservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    # Vérification des permissions
    if request.user.role != 'admin' and reservation.user != request.user:
        messages.error(request, 'Permission refusée')
        return redirect('reservations:reservation_list_orchestrated')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        result = ReservationOrchestrationService.cancel_reservation(
            reservation=reservation,
            cancelled_by=request.user,
            reason=reason
        )
        
        if result['success']:
            messages.success(request, 'Réservation annulée avec succès')
            if result['refund_amount'] > 0:
                messages.info(request, f'Remboursement de {result["refund_amount"]} FCFA traité')
        else:
            messages.error(request, f"Erreur: {result['error']}")
        
        return redirect(f"{reverse_lazy('reservations:reservation_list_orchestrated')}?reservation_cancelled={reservation.id}#confirmation")
    
    return render(request, 'reservations/annulation_reservation.html', {
        'reservation': reservation
    })


@login_required
def reservation_confirmation_view(request, pk):
    """Vue de confirmation après création de réservation"""
    reservation = get_object_or_404(Reservation, id=pk)
    
    # Vérification des permissions
    if request.user.role != 'admin' and reservation.user != request.user:
        messages.error(request, 'Permission refusée')
        return redirect('reservations:reservation_list_orchestrated')
    
    # Récupérer les détails complets via le service
    result = ReservationOrchestrationService.get_reservation_details(pk)
    
    context = {
        'reservation': reservation
    }
    
    if result['success']:
        details = result['details']
        context.update({
            'payment': details['payment'],
            'price_history': details['price_history'],
            'subscription': details['subscription']
        })
    
    return render(request, 'reservations/reservation_confirmation.html', context)


@login_required
def dashboard_analytics_view(request):
    """Tableau de bord analytics pour les admins"""
    if request.user.role != 'admin':
        messages.error(request, 'Accès réservé aux administrateurs')
        return redirect('reservations:reservation_list_orchestrated')
    
    # Récupérer les analytics
    dashboard_data = ReservationAnalyticsService.get_dashboard_summary()
    
    return render(request, 'reservations/dashboard_analytics.html', {
        'dashboard_data': dashboard_data
    })
