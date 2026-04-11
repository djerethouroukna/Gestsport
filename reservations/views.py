from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.http import JsonResponse, HttpResponseNotFound, Http404
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)

from .models import Reservation, ReservationStatus
from .forms import ReservationForm
from terrains.models import Terrain
from .serializers import ReservationSerializer

class ReservationListView(LoginRequiredMixin, ListView):
    """Vue pour la liste des réservations"""
    model = Reservation
    template_name = 'reservations/reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 12

    def get_queryset(self):
        user = self.request.user
        queryset = Reservation.objects.select_related('terrain', 'user')
        
        # Filtrer selon le rôle
        if user.role == 'admin':
            # Admin voit toutes les réservations
            queryset = queryset.all()
        elif user.role == 'coach':
            # Coach voit uniquement ses propres réservations
            queryset = queryset.filter(user=user)
        else:  # player
            # Player voit uniquement ses propres réservations
            queryset = queryset.filter(user=user)
        
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
        
        # Statistiques
        queryset = self.get_queryset()
        total_reservations = queryset.count()
        confirmed_count = queryset.filter(status='confirmed').count()
        pending_count = queryset.filter(status='pending').count()
        cancelled_count = queryset.filter(status='cancelled').count()
        
        # Pourcentages simples
        if total_reservations > 0:
            confirmed_percentage = (confirmed_count / total_reservations) * 100
            pending_percentage = (pending_count / total_reservations) * 100
            cancelled_percentage = (cancelled_count / total_reservations) * 100
            # Performance basée sur le taux de confirmation
            performance_percentage = confirmed_percentage
        else:
            confirmed_percentage = pending_percentage = cancelled_percentage = performance_percentage = 0
        
        context['total_reservations'] = total_reservations
        context['confirmed_count'] = confirmed_count
        context['pending_count'] = pending_count
        context['cancelled_count'] = cancelled_count
        context['confirmed_percentage'] = confirmed_percentage
        context['pending_percentage'] = pending_percentage
        context['cancelled_percentage'] = cancelled_percentage
        context['performance_percentage'] = performance_percentage
        
        # Activités confirmées disponibles pour réservation
        from activities.models import Activity, ActivityStatus
        user = self.request.user
        
        if user.role == 'admin':
            # Admin voit toutes les activités confirmées
            confirmed_activities = Activity.objects.filter(status=ActivityStatus.CONFIRMED)
        elif user.role == 'coach':
            # Coach voit ses activités confirmées
            confirmed_activities = Activity.objects.filter(
                status=ActivityStatus.CONFIRMED,
                coach=user
            )
        else:
            # Player ne voit rien (pas de création de réservation)
            confirmed_activities = Activity.objects.none()
        
        context['confirmed_activities'] = confirmed_activities
        
        return context

class ReservationDetailView(LoginRequiredMixin, DetailView):
    """Vue pour les détails d'une réservation"""
    model = Reservation
    template_name = 'reservations/reservation_detail.html'
    context_object_name = 'reservation'

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        
        # Vérifier les permissions
        if user.role == 'player':
            # Les joueurs peuvent voir uniquement les réservations confirmées
            if obj.status != ReservationStatus.CONFIRMED:
                raise Http404("Cette réservation n'est pas accessible")
        elif user.role == 'coach':
            # Les coachs peuvent voir uniquement leurs propres réservations
            if obj.user != user:
                raise Http404("Cette réservation n'est pas accessible")
        
        return obj

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Http404:
            # Rediriger les joueurs vers le calendrier pour les réservations non accessibles
            if request.user.role == 'player':
                return redirect('reservations:reservation_calendar')
            raise

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservation = self.object
        
        # Calculer la durée
        duration = reservation.end_time - reservation.start_time
        total_minutes = int(duration.total_seconds() / 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        context['duration_hours'] = hours
        context['duration_minutes'] = minutes
        context['duration_decimal'] = round(total_minutes / 60, 1)
        
        # Calculer la TVA (18% comme dans la facture)
        from decimal import Decimal
        tax_rate = Decimal('0.18')  # 18% de TVA
        subtotal = reservation.total_amount
        tax_amount = subtotal * tax_rate
        total_with_tax = subtotal + tax_amount
        
        context['subtotal'] = subtotal
        context['tax_rate'] = tax_rate
        context['tax_amount'] = tax_amount
        context['total_with_tax'] = total_with_tax
        
        # Réservations similaires sur le même terrain
        context['related_reservations'] = Reservation.objects.filter(
            terrain=reservation.terrain,
            start_time__date=reservation.start_time.date(),
            status__in=['confirmed', 'pending']
        ).exclude(id=reservation.id)[:6]
        
        return context

def reservation_create_view(request):
    """Vue de création de réservation OBLIGATOIREMENT liée à une activité"""
    print("=== RÉSERVATION CREATE VIEW ===")
    print(f"Method: {request.method}")
    print(f"User: {request.user}")
    print(f"GET: {request.GET}")
    
    # Imports nécessaires pour toute la fonction
    from .forms import ReservationForm
    from .models import ReservationStatus
    from django.contrib import messages
    from terrains.models import Terrain
    from django.shortcuts import redirect
    
    # Vérifier OBLIGATOIREMENT la présence de activity_id
    activity_id = request.GET.get('activity_id')
    if not activity_id:
        messages.error(request, 'Vous devez d\'abord créer ou sélectionner une activité avant de faire une réservation.')
        return redirect('activities:activity_list')
    
    # Vérifier que l'activité existe
    try:
        from activities.models import Activity, ActivityStatus
        activity = Activity.objects.get(id=activity_id)
    except Activity.DoesNotExist:
        messages.error(request, 'Cette activité n\'existe pas.')
        return redirect('activities:activity_list')
    
    # Vérifier que l'utilisateur a le droit de réserver cette activité
    if activity.coach != request.user and request.user.role != 'admin':
        messages.error(request, 'Vous n\'êtes pas autorisé à réserver cette activité.')
        return redirect('activities:activity_list')
    
    if request.method == 'POST':
        print("POST reçu!")
        print(f"POST data: {request.POST}")
        
        form = ReservationForm(request.POST)
        if form.is_valid():
            print("Formulaire valide!")
            
            # Créer la réservation LIÉE À L'ACTIVITÉ
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.status = ReservationStatus.PENDING
            reservation.activity = activity  # LIAISON OBLIGATOIRE
            reservation.save()
            
            # Calculer le montant total basé sur l'activité
            from .utils import calculate_reservation_amount
            reservation.total_amount = calculate_reservation_amount(reservation)
            reservation.save()
            
            print(f"Réservation créée: {reservation.id} liée à l'activité: {activity.title}")
            
            messages.success(request, f'Votre réservation pour l\'activité "{activity.title}" a été créée avec succès!')
            
            # Rediriger vers la page de paiement
            print(f"Redirection vers paiement pour réservation {reservation.id}")
            return redirect('reservations:payment_checkout', pk=reservation.id)
        else:
            print("Formulaire invalide!")
            print(f"Erreurs: {form.errors}")
    
    # Préparer le contexte avec l'activité
    context = {
        'activity': activity,
        'terrains': Terrain.objects.all(),
        'form': ReservationForm(initial={
            'terrain': activity.terrain,
            'start_time': activity.start_time,
            'end_time': activity.end_time,
            'notes': f'Réservation pour l\'activité: {activity.title}'
        }),
        'is_activity_confirmed': activity.status == ActivityStatus.CONFIRMED,
        'prefilled_data': {
            'terrain': activity.terrain.id,
            'start_time': activity.start_time,
            'end_time': activity.end_time,
            'notes': f'Réservation pour l\'activité: {activity.title}'
        }
    }
    
    from django.shortcuts import render
    return render(request, 'reservations/reservation_create.html', context)

@login_required
def reservation_from_activity(request, activity_id):
    """Vue pour réserver une activité confirmée"""
    print(f"=== RÉSERVATION DEPUIS ACTIVITÉ {activity_id} ===")
    
    from activities.models import Activity
    activity = get_object_or_404(Activity, id=activity_id)
    
    print(f"Activité: {activity}")
    print(f"Status: {activity.status}")
    print(f"Coach: {activity.coach}")
    print(f"User: {request.user}")
    
    # Vérifier si l'activité est confirmée
    if activity.status != 'confirmed':
        messages.error(request, "Cette activité n'est pas encore confirmée")
        return redirect('activities:detail', activity_id)
    
    # Vérifier si l'utilisateur est le coach de l'activité
    if activity.coach != request.user:
        messages.error(request, "Vous n'êtes pas le coach de cette activité")
        return redirect('activities:detail', activity_id)
    
    # Pré-remplir le formulaire avec les données de l'activité
    initial_data = {
        'terrain': activity.terrain.id,
        'start_time': activity.start_time.strftime('%Y-%m-%dT%H:%M'),
        'end_time': activity.end_time.strftime('%Y-%m-%dT%H:%M'),
        'notes': f"Réservation pour l'activité: {activity.title}"
    }
    
    print(f"Initial data: {initial_data}")
    
    if request.method == 'POST':
        print("Méthode POST reçu")
        form = ReservationForm(request.POST, initial=initial_data)
        if form.is_valid():
            print("Formulaire valide!")
            
            # Créer la réservation
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.activity = activity
            reservation.status = ReservationStatus.PENDING
            reservation.save()
            
            # Calculer le montant total
            from .utils import calculate_reservation_amount
            reservation.total_amount = calculate_reservation_amount(reservation)
            reservation.save()
            
            print(f"Réservation créée: {reservation.id}")
            print(f"Montant: {reservation.total_amount}")
            
            messages.success(request, 'Votre réservation a été créée avec succès!')
            
            # Redirection vers paiement
            print(f"Redirection vers paiement pour réservation {reservation.id}")
            return redirect('reservations:payment_checkout', pk=reservation.id)
        else:
            print("Formulaire invalide!")
            print(f"Erreurs: {form.errors}")
    else:
        print("Méthode GET - affichage formulaire")
        form = ReservationForm(initial=initial_data)
        
        # Rendre les champs non modifiables
        form.fields['terrain'].widget.attrs['readonly'] = True
        form.fields['start_time'].widget.attrs['readonly'] = True
        form.fields['end_time'].widget.attrs['readonly'] = True
    
    context = {
        'form': form,
        'activity': activity
    }
    
    return render(request, 'reservations/reservation_from_activity.html', context)

class ReservationCreateView(LoginRequiredMixin, CreateView):
    """Vue pour créer une réservation"""
    model = Reservation
    template_name = 'reservations/reservation_create.html'
    fields = ['terrain', 'start_time', 'end_time', 'notes']
    success_url = reverse_lazy('reservations:reservation_list')

    def dispatch(self, request, *args, **kwargs):
        print("=== RESERVATION CREATE VIEW DISPATCH ===")
        print(f"Method: {request.method}")
        print(f"User: {request.user}")
        print(f"GET: {request.GET}")
        print(f"POST: {request.POST}")
        print("=== END DISPATCH ===")
        print("=== DEBUG dispatch ===")
        print(f"User: {request.user}, Role: {request.user.role}")
        print(f"Method: {request.method}")
        print(f"GET params: {request.GET}")
        print(f"POST data: {request.POST}")
        
        # Les admins et coaches peuvent créer des réservations
        if request.user.role not in ['admin', 'coach']:
            from django.http import Http404
            raise Http404("Vous n'avez pas la permission de créer une réservation")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['terrains'] = Terrain.objects.all()
        
        # Gérer le paramètre activity_id si présent
        activity_id = self.request.GET.get('activity_id')
        if activity_id:
            try:
                from activities.models import Activity, ActivityStatus
                activity = Activity.objects.get(id=activity_id)
                context['activity'] = activity
                
                # Vérifier si l'activité est confirmée
                is_confirmed = activity.status == ActivityStatus.CONFIRMED
                context['is_activity_confirmed'] = is_confirmed
                
                # Pré-remplir les champs avec les données de l'activité
                context['prefilled_data'] = {
                    'terrain': activity.terrain.id,
                    'start_time': activity.start_time,
                    'end_time': activity.end_time,
                    'notes': f'Réservation pour l\'activité: {activity.title}'
                }
            except Activity.DoesNotExist:
                pass
        
        return context

    def form_valid(self, form):
        print("=== DEBUG form_valid ===")
        print(f"Form data: {form.cleaned_data}")
        
        form.instance.user = self.request.user
        form.instance.status = ReservationStatus.PENDING
        
        # Validation de disponibilité
        terrain = form.cleaned_data['terrain']
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']
        
        print(f"Terrain: {terrain}, Start: {start_time}, End: {end_time}")
        
        # Vérifier les conflits avec autres réservations
        conflicting = Reservation.objects.filter(
            terrain=terrain,
            status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()
        
        print(f"Conflicting reservations: {conflicting}")

        # Vérifier les conflits avec les activités programmées
        from activities.models import Activity, ActivityStatus
        activity_conflict = Activity.objects.filter(
            terrain=terrain,
            status=ActivityStatus.CONFIRMED,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(id=self.request.GET.get('activity_id')).exists()  # Exclure l'activité actuelle
        
        print(f"Conflicting activities: {activity_conflict}")

        # Vérifier la disponibilité via le service TimeSlot
        from timeslots.services import TimeSlotService as TSService
        is_available_ts, ts_conflicts = TSService.check_availability(
            terrain, start_time, end_time
        )
        
        print(f"TimeSlot available: {is_available_ts}, conflicts: {ts_conflicts}")

        if conflicting or activity_conflict or not is_available_ts:
            msg = 'Ce terrain n\'est pas disponible pour cette période.'
            # Détail des conflits pour l'admin
            if activity_conflict:
                msg += ' Une activité est programmée.'
            if not is_available_ts and ts_conflicts:
                msg += f' Créeaux bloqués: {len(ts_conflicts)}.'
            print(f"Form invalid: {msg}")
            form.add_error(None, msg)
            return self.form_invalid(form)

        messages.success(self.request, 'Votre réservation a été créée et est en attente de validation.')
        print("Form valid, redirecting...")
        return super().form_valid(form)

    def form_invalid(self, form):
        print("=== DEBUG form_invalid ===")
        print(f"Form errors: {form.errors}")
        print(f"Non-field errors: {form.non_field_errors()}")
        return super().form_invalid(form)

class ReservationUpdateView(LoginRequiredMixin, UpdateView):
    """Vue pour modifier une réservation"""
    model = Reservation
    template_name = 'reservations/reservation_create.html'
    fields = ['start_time', 'end_time', 'notes']
    success_url = reverse_lazy('reservations:reservation_list')

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        
        # Vérifier les permissions
        if user.role == 'player':
            from django.http import Http404
            raise Http404("Vous n'avez pas la permission de modifier cette réservation")
        
        # Seules les réservations en attente ou confirmées peuvent être modifiées
        if obj.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
            from django.http import Http404
            raise Http404("Cette réservation ne peut plus être modifiée")
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['terrains'] = Terrain.objects.all()
        context['is_update'] = True
        return context

    def form_valid(self, form):
        # Validation de disponibilité
        terrain = self.object.terrain
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']
        
        # Vérifier les conflits (exclure cette réservation)
        conflicting = Reservation.objects.filter(
            terrain=terrain,
            status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(id=self.object.id).exists()
        
        if conflicting:
            form.add_error(None, 'Ce terrain n\'est pas disponible pour cette période')
            return self.form_invalid(form)
        
        messages.success(self.request, 'Votre réservation a été modifiée.')
        return super().form_valid(form)

@login_required
@require_POST
def cancel_reservation(request, reservation_id):
    """Annuler une réservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    user = request.user
    
    # Vérifier les permissions
    if user.role == 'player':
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    # Vérifier que la réservation peut être annulée
    if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
        return JsonResponse({'error': 'Cette réservation ne peut plus être annulée'}, status=400)
    
    # Vérifier le délai d'annulation (24h)
    if reservation.start_time <= timezone.now() + timezone.timedelta(hours=24):
        return JsonResponse({'error': 'Les annulations doivent être faites au moins 24h à l\'avance'}, status=400)
    
    reservation.status = ReservationStatus.CANCELLED
    reservation.save()
    
    # Envoyer notification à l'utilisateur
    from notifications.utils import NotificationService
    NotificationService.notify_reservation_cancelled(reservation)
    
    messages.success(request, 'Votre réservation a été annulée.')
    return JsonResponse({'success': True})

@login_required
@require_POST
def confirm_reservation(request, reservation_id):
    """Confirmer une réservation (admin uniquement)"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    user = request.user
    
    # Vérifier les permissions (seul admin peut confirmer)
    if user.role != 'admin':
        return JsonResponse({'error': 'Non autorisé - seul un administrateur peut confirmer une réservation'}, status=403)
    
    # Vérifier que la réservation est en attente
    if reservation.status != ReservationStatus.PENDING:
        return JsonResponse({'error': 'Cette réservation ne peut plus être confirmée'}, status=400)
    
    reservation.status = ReservationStatus.CONFIRMED
    reservation.save()
    
    # Envoyer notification à l'utilisateur
    try:
        from notifications.utils import NotificationService
        NotificationService.notify_reservation_confirmed(reservation)
    except:
        pass  # Si le service de notification n'existe pas
    
    # Créer une notification pour le coach
    try:
        from payment_notification_service import PaymentNotificationService
        PaymentNotificationService.create_confirmation_notification(reservation, user)
    except Exception as e:
        print(f"Erreur notification confirmation: {e}")
    
    messages.success(request, 'La réservation a été confirmée.')
    return JsonResponse({'success': True})

@login_required
@require_POST
def reject_reservation(request, reservation_id):
    """Rejeter une réservation (admin uniquement)"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    user = request.user
    
    # Vérifier les permissions (seul admin peut rejeter)
    if user.role != 'admin':
        return JsonResponse({'error': 'Non autorisé - seul un administrateur peut rejeter une réservation'}, status=403)
    
    # Vérifier que la réservation est en attente
    if reservation.status != ReservationStatus.PENDING:
        return JsonResponse({'error': 'Cette réservation ne peut plus être rejetée'}, status=400)
    
    reservation.status = ReservationStatus.REJECTED
    reservation.save()
    
    # Envoyer notification à l'utilisateur
    from notifications.utils import NotificationService
    NotificationService.notify_reservation_rejected(reservation)
    
    messages.success(request, 'La réservation a été rejetée.')
    return JsonResponse({'success': True})

@login_required
@require_POST
def approve_cancel(request, reservation_id):
    """Approuver l'annulation d'une réservation (entraîneur/admin)"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    user = request.user
    
    # Vérifier les permissions (seuls entraîneur et admin peuvent approuver)
    if user.role not in ['coach', 'admin']:
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    # Vérifier que la réservation est en attente d'annulation
    if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
        return JsonResponse({'error': 'Cette réservation ne peut plus être annulée'}, status=400)
    
    reservation.status = ReservationStatus.CANCELLED
    reservation.save()
    
    # Envoyer notification à l'utilisateur
    from notifications.utils import NotificationService
    NotificationService.notify_reservation_cancelled(reservation)
    
    messages.success(request, 'L\'annulation a été approuvée.')
    return JsonResponse({'success': True})

@login_required
def payment_checkout(request, pk):
    """Page de checkout pour une réservation spécifique"""
    print(f"=== PAYMENT CHECKOUT pour réservation {pk} ===")
    reservation = get_object_or_404(Reservation, pk=pk)
    user = request.user
    
    print(f"Réservation: {reservation}")
    print(f"User: {user} (role: {user.role})")
    print(f"Reservation user: {reservation.user}")
    print(f"Reservation status: {reservation.status}")
    print(f"Has payment: {reservation.has_payment}")
    print(f"Has payment submission: {reservation.has_payment_submission}")

    # L'utilisateur ne peut payer que sa propre réservation à moins qu'il soit admin
    if reservation.user != user and user.role != 'admin':
        print("ERREUR: Permission refusée")
        messages.error(request, 'Non autorisé à payer cette réservation.')
        return redirect('reservations:reservation_detail', pk=pk)
    
    # Vérifier si la réservation est confirmée
    if reservation.status != 'confirmed':
        print("ERREUR: Réservation non confirmée")
        messages.warning(request, 'Cette réservation n\'est pas encore confirmée par l\'administrateur.')
        return redirect('reservations:reservation_detail', pk=pk)
    
    # Vérifier si déjà payé
    if reservation.is_paid:
        print("ERREUR: Déjà payé")
        messages.info(request, 'Cette réservation est déjà payée.')
        return redirect('reservations:reservation_detail', pk=pk)
    
    # Calculs financiers
    subtotal = reservation.total_amount
    tax_rate = 0.18  # 18% TVA
    tax_amount = subtotal * Decimal(str(tax_rate))
    total_with_tax = subtotal + tax_amount
    
    print(f"Calculs: Subtotal={subtotal}, Tax={tax_amount}, Total={total_with_tax}")
    
    try:
        subtotal = Decimal(str(subtotal))
        tax_amount = subtotal * tax_rate
        total_with_tax = subtotal + tax_amount
    except (TypeError, ValueError) as e:
        messages.error(request, f'Erreur lors du calcul du montant: {e}')
        return redirect('reservations:reservation_detail', pk=pk)

    # Montrer la page de checkout avec le nouveau système de soumission
    return render(request, 'payments/checkout.html', {
        'reservation': reservation,
        'duration': duration,
        'subtotal': subtotal,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'total_with_tax': total_with_tax,
    })


@login_required
def reservation_calendar(request):
    """Vue pour le calendrier des réservations"""
    user = request.user
    
    # Filtrer les réservations selon le rôle
    if user.role == 'admin':
        reservations = Reservation.objects.select_related('terrain', 'user')
    elif user.role == 'coach':
        reservations = Reservation.objects.select_related('terrain', 'user')
    else:  # player
        # Les joueurs voient toutes les réservations pour consulter le programme
        reservations = Reservation.objects.select_related('terrain', 'user')
    
    # Préparer les données pour FullCalendar
    reservations_data = []
    for res in reservations:
        reservations_data.append({
            'id': res.id,
            'terrain_name': res.terrain.name,
            'user_name': res.user.get_full_name() or res.user.username,
            'start_time': res.start_time.isoformat(),
            'end_time': res.end_time.isoformat(),
            'status': res.status,
            'notes': res.notes
        })
    
    # Statistiques
    now = timezone.now()
    month_start = now.replace(day=1)
    week_start = now - timezone.timedelta(days=now.weekday())
    
    context = {
        'reservations_json': json.dumps(reservations_data),
        'terrains': Terrain.objects.all(),
        'total_reservations': reservations.count(),
        'month_reservations': reservations.filter(start_time__gte=month_start).count(),
        'week_reservations': reservations.filter(start_time__gte=week_start).count(),
        'pending_reservations': reservations.filter(status='pending').count(),
        'upcoming_reservations': reservations.filter(
            start_time__gte=now,
            status__in=['confirmed', 'pending']
        ).order_by('start_time')[:5]
    }
    
    return render(request, 'reservations/reservation_calendar.html', context)


@login_required
def payment_success(request, pk):
    """Page de succès après paiement"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Vérifier si l'utilisateur peut voir cette page
    if reservation.user != request.user and request.user.role != 'admin':
        messages.error(request, 'Non autorisé')
        return redirect('reservations:reservation_list')
    
    # Vérifier si le paiement a été traité
    if reservation.payment_status == 'paid':
        messages.success(request, 'Paiement effectué avec succès! Votre réservation est confirmée.')
    else:
        messages.info(request, 'Votre paiement est en cours de validation.')
    
    return redirect('reservations:reservation_detail', pk=pk)


@login_required
def payment_cancel(request, pk):
    """Page d'annulation de paiement"""
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Vérifier si l'utilisateur peut voir cette page
    if reservation.user != request.user and request.user.role != 'admin':
        messages.error(request, 'Non autorisé')
        return redirect('reservations:reservation_list')
    
    messages.warning(request, 'Paiement annulé. Vous pouvez réessayer plus tard.')
    
    return redirect('reservations:reservation_list')


@login_required
def download_ticket_redirect(request, reservation_id):
    """Redirection vers le téléchargement de ticket (évite les problèmes d'URL)"""
    # Rediriger vers la vraie URL de téléchargement dans l'app tickets
    from django.urls import reverse
    return redirect(reverse('tickets:download', kwargs={'reservation_id': reservation_id}))


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
            modified__date=timezone.now().date()
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
