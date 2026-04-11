# payments/views_payment_submission.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.db import transaction
from django.views import View

from reservations.models import Reservation
from .models import PaymentSubmission, PaymentSubmissionStatus
from .services import PaymentSubmissionService


class PaymentSubmissionView(LoginRequiredMixin, View):
    """Vue pour soumettre un paiement"""
    
    def get(self, request, reservation_id):
        """Affiche le formulaire de soumission de paiement"""
        reservation = get_object_or_404(Reservation, id=reservation_id)
        
        # Vérifications
        if reservation.user != request.user and request.user.role != 'admin':
            messages.error(request, "Vous n'avez pas accès à cette réservation")
            return redirect('reservations:reservation_list')
        
        if reservation.has_payment:
            messages.error(request, "Cette réservation a déjà été payée")
            return redirect('reservations:reservation_detail', reservation_id)
        
        if reservation.has_payment_submission:
            messages.info(request, "Cette réservation a déjà une soumission de paiement en attente")
            return redirect('reservations:reservation_detail', reservation_id)
        
        context = {
            'reservation': reservation,
            'duration': reservation.duration_minutes / 60,
        }
        
        return render(request, 'payments/payment_submission.html', context)
    
    def post(self, request, reservation_id):
        """Traite la soumission de paiement"""
        reservation = get_object_or_404(Reservation, id=reservation_id)
        
        # Vérifications
        if reservation.user != request.user and request.user.role != 'admin':
            return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
        
        if reservation.has_payment:
            return JsonResponse({'success': False, 'error': 'Réservation déjà payée'}, status=400)
        
        if reservation.has_payment_submission:
            return JsonResponse({'success': False, 'error': 'Soumission déjà existante'}, status=400)
        
        try:
            # Debug: afficher toutes les données reçues
            print(f"POST data reçu: {dict(request.POST)}")
            print(f"User: {request.user}")
            print(f"Reservation: {reservation}")
            
            # Récupérer les données du formulaire
            payment_data = {
                'payment_method_type': request.POST.get('payment_method_type'),
                'amount': request.POST.get('amount'),
                'notes': request.POST.get('notes', ''),
            }
            
            print(f"Payment data initial: {payment_data}")
            
            # Ajouter les détails spécifiques selon le type
            if payment_data['payment_method_type'] == 'card':
                payment_data.update({
                    'card_number': request.POST.get('card_number', ''),
                    'card_holder_name': request.POST.get('card_holder_name', ''),
                    'card_expiry': request.POST.get('card_expiry', ''),
                    'card_cvv': request.POST.get('card_cvv', ''),
                })
            elif payment_data['payment_method_type'] == 'mobile_money':
                payment_data.update({
                    'mobile_number': request.POST.get('mobile_number', ''),
                    'mobile_provider': request.POST.get('mobile_provider', ''),
                })
            
            # Créer la soumission
            submission = PaymentSubmissionService.create_payment_submission(
                reservation, payment_data, request
            )
            
            print(f"Soumission créée avec succès: {submission.id}")
            return JsonResponse({
                'success': True,
                'message': 'Votre soumission de paiement a été enregistrée et est en attente de validation',
                'submission_id': str(submission.id),
                'redirect_url': reverse_lazy('reservations:reservation_detail', kwargs={'pk': reservation_id})
            })
            
        except Exception as e:
            import traceback
            print(f"Erreur dans payment_submission: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class PaymentSubmissionListView(LoginRequiredMixin, ListView):
    """Vue pour lister les soumissions de paiement (admin uniquement)"""
    model = PaymentSubmission
    template_name = 'payments/payment_submission_list.html'
    context_object_name = 'submissions'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        # Vérifier si l'utilisateur est admin
        if request.user.role != 'admin':
            messages.error(request, "Accès non autorisé. Cette page est réservée aux administrateurs.")
            return redirect('dashboard_admin')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.select_related('reservation', 'user', 'reservation__terrain').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques
        total = PaymentSubmission.objects.count()
        pending_count = PaymentSubmission.objects.filter(status='submitted').count()
        validated = PaymentSubmission.objects.filter(status='validated').count()
        rejected = PaymentSubmission.objects.filter(status='rejected').count()
        validation_rate = (validated / total * 100) if total > 0 else 0
        
        context.update({
            'total': total,
            'pending_count': pending_count,
            'validated': validated,
            'rejected': rejected,
            'validation_rate': validation_rate,
            'current_status': self.request.GET.get('status', ''),
            'pending_submissions_count': pending_count,  # Pour le menu sidebar
        })
        
        return context


class PaymentSubmissionDetailView(LoginRequiredMixin, DetailView):
    """Vue pour voir les détails d'une soumission de paiement (admin uniquement)"""
    model = PaymentSubmission
    template_name = 'payments/payment_submission_detail.html'
    context_object_name = 'submission'
    
    def dispatch(self, request, *args, **kwargs):
        # Vérifier si l'utilisateur est admin
        if request.user.role != 'admin':
            messages.error(request, "Accès non autorisé. Cette page est réservée aux administrateurs.")
            return redirect('dashboard_admin')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculer la durée
        reservation = self.object.reservation
        duration = reservation.duration_minutes / 60
        
        # Vérifier si l'utilisateur peut valider
        can_validate = (
            self.request.user.role == 'admin' and 
            self.object.status in ['submitted', 'under_review']
        )
        
        context.update({
            'duration': duration,
            'can_validate': can_validate,
            'pending_submissions_count': PaymentSubmission.objects.filter(status='submitted').count(),
        })
        
        return context


@require_POST
@login_required
def validate_payment_submission(request, submission_id):
    """Vue pour valider une soumission de paiement"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
    
    try:
        notes = request.POST.get('notes', '')
        # print(f"Tentative de validation: submission_id={submission_id}, user={request.user}, notes={notes}")
        
        payment = PaymentSubmissionService.validate_payment_submission(
            submission_id, request.user, notes
        )
        
        # messages.success(request, 'Paiement validé avec succès')  # Commenté pour éviter le doublon avec JavaScript
        
        return JsonResponse({
            'success': True,
            'message': 'Paiement validé avec succès',
            'payment_id': str(payment.id),
            'redirect_url': reverse_lazy('payment_submissions:list')
        })
        
    except Exception as e:
        import traceback
        print(f"Erreur validation: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
@login_required
def reject_payment_submission(request, submission_id):
    """Vue pour rejeter une soumission de paiement"""
    # Logs de débogage commentés pour la production
    # print(f"DEBUG: reject_payment_submission appelé avec submission_id={submission_id}")
    # print(f"DEBUG: user={request.user}, role={request.user.role}")
    
    if request.user.role != 'admin':
        # print(f"DEBUG: Accès refusé - user role is {request.user.role}")
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
    
    try:
        reason = request.POST.get('reason', '')
        # print(f"DEBUG: reason={reason}")
        
        submission = PaymentSubmissionService.reject_payment_submission(
            submission_id, request.user, reason
        )
        # print(f"DEBUG: submission rejetée: {submission.id}")
        
        # messages.success(request, 'Paiement rejeté avec succès')  # Commenté pour éviter le doublon avec JavaScript
        
        return JsonResponse({
            'success': True,
            'message': 'Paiement rejeté avec succès',
            'submission_id': str(submission.id),
            'redirect_url': reverse_lazy('payment_submissions:list')
        })
        
    except Exception as e:
        print(f"DEBUG: Erreur lors du rejet: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


class PaymentSubmissionDashboardView(LoginRequiredMixin, View):
    """Vue du tableau de bord des soumissions de paiement"""
    
    def get(self, request):
        """Affiche le tableau de bord des soumissions"""
        if request.user.role != 'admin':
            messages.error(request, "Accès réservé aux administrateurs")
            return redirect('dashboard:home')
        
        # Statistiques
        stats = PaymentSubmissionService.get_submission_statistics()
        
        # Soumissions récentes
        recent_submissions = PaymentSubmission.objects.filter(
            status__in=[PaymentSubmissionStatus.SUBMITTED, PaymentSubmissionStatus.UNDER_REVIEW]
        ).order_by('-created_at')[:10]
        
        context = {
            'stats': stats,
            'recent_submissions': recent_submissions,
        }
        
        return render(request, 'payments/payment_submission_dashboard.html', context)


# Vue de mise à jour du statut
@require_POST
@login_required
def update_submission_status(request, submission_id):
    """Met à jour le statut d'une soumission"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
    
    try:
        submission = get_object_or_404(PaymentSubmission, id=submission_id)
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status == PaymentSubmissionStatus.VALIDATED:
            payment = PaymentSubmissionService.validate_payment_submission(
                submission_id, request.user, notes
            )
            return JsonResponse({
                'success': True,
                'message': 'Paiement validé',
                'payment_id': str(payment.id)
            })
        
        elif new_status == PaymentSubmissionStatus.REJECTED:
            submission = PaymentSubmissionService.reject_payment_submission(
                submission_id, request.user, notes
            )
            return JsonResponse({
                'success': True,
                'message': 'Paiement rejeté',
                'submission_id': str(submission.id)
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Statut invalide'}, status=400)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
