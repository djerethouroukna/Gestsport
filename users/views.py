from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, DetailView, UpdateView, DeleteView, View, ListView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm

from .forms import PublicRegistrationForm, CustomRegistrationForm, UserUpdateForm, CustomPasswordChangeForm, AdminUserCreationForm
from .models import User, UserPreferences

class CustomLoginView(CreateView):
    template_name = 'login_new.html'
    
    def get(self, request, *args, **kwargs):
        from django.contrib.auth.forms import AuthenticationForm
        if request.user.is_authenticated:
            # Rediriger l'utilisateur connecté vers son tableau de bord selon son rôle
            if request.user.role == 'admin':
                return redirect('dashboard_admin')
            elif request.user.role == 'coach':
                return redirect('dashboard_coach')
            else:
                return redirect('dashboard_player')
        form = AuthenticationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        from django.contrib.auth.forms import AuthenticationForm
        form = AuthenticationForm(request=request, data=request.POST)
        next_url = request.POST.get('next') or request.GET.get('next') or None

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenue {user.get_full_name() or user.email} !')
            # Si un 'next' explicite existe, on le respecte
            if next_url:
                return redirect(next_url)
            # Sinon on redirige selon le rôle
            if user.role == 'admin':
                return redirect('dashboard_admin')
            elif user.role == 'coach':
                return redirect('dashboard_coach')
            else:
                return redirect('dashboard_player')
        
        # Renvoyer le formulaire avec les erreurs pour affichage
        return render(request, self.template_name, {'form': form})

class PublicRegisterView(CreateView):
    template_name = 'register_new.html'
    form_class = PublicRegistrationForm
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        messages.success(self.request, 'Votre compte a été créé avec succès ! Un email de validation vous a été envoyé.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erreur lors de la création du compte. Veuillez vérifier les informations.')
        return super().form_invalid(form)


class EmailVerificationView(View):
    """Vue pour valider l'email via le lien envoyé par email"""
    
    def get(self, request, uidb64, token):
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from django.contrib.auth.tokens import default_token_generator
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            # Valider l'email
            user.email_verified = True
            user.is_active = True
            user.save()
            
            # Envoyer un email de bienvenue
            from notifications.email_service import EmailService
            EmailService.send_welcome_email(user)
            
            messages.success(request, 'Votre email a été validé avec succès ! Vous pouvez maintenant vous connecter.')
            return redirect('users:login')
        else:
            messages.error(request, 'Le lien de validation est invalide ou a expiré.')
            return redirect('users:login')

class RegisterView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    template_name = 'register_admin.html'
    
    def test_func(self):
        # Seuls les admins peuvent accéder à la page d'inscription admin
        return self.request.user.is_authenticated and self.request.user.role == 'admin'
    
    def handle_no_permission(self):
        messages.error(self.request, "Seuls les administrateurs peuvent créer des comptes.")
        return redirect('reservations:reservation_list')
    
    def get_form_class(self):
        return AdminUserCreationForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        messages.success(self.request, 'Le compte a été créé avec succès.')
        return reverse_lazy('users:user_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Le compte {self.object.get_full_name()} a été créé avec succès.')
        return response

class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'users/profile.html'
    context_object_name = 'user'
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Importer les modèles
        from reservations.models import Reservation
        from activities.models import Activity
        from payments.models import Payment
        
        # Statistiques RÉELLES
        context['reservations_count'] = Reservation.objects.filter(user=user).count()
        context['activities_count'] = Activity.objects.filter(coach=user).count() + Activity.objects.filter(participants=user).count()
        
        # Calculer les dépenses réelles
        completed_payments = Payment.objects.filter(user=user, status='completed')
        total_spent = sum(payment.amount for payment in completed_payments)
        context['total_spent'] = total_spent
        
        # Points calculés selon les réservations et activités
        points = (context['reservations_count'] * 10) + (context['activities_count'] * 5)
        context['user_points'] = points
        
        # Pourcentages de performance (basés sur l'activité récente)
        from datetime import datetime, timedelta
        last_month = datetime.now() - timedelta(days=30)
        
        recent_reservations = Reservation.objects.filter(user=user, start_time__gte=last_month).count()
        old_reservations = Reservation.objects.filter(user=user, start_time__lt=last_month).count()
        
        if old_reservations > 0:
            reservation_performance = ((recent_reservations - old_reservations) / old_reservations) * 100
        else:
            reservation_performance = recent_reservations * 10  # Croissance initiale
        
        context['reservation_performance'] = round(reservation_performance, 1)
        
        # Activités récentes pour le coach
        if hasattr(user, 'is_coach') and user.is_coach:
            context['recent_activities'] = Activity.objects.filter(coach=user).order_by('-start_time')[:3]
        else:
            context['recent_activities'] = []
        
        # Autres statistiques
        context['upcoming_reservations'] = Reservation.objects.filter(user=user, status='confirmed').count()
        context['past_reservations'] = Reservation.objects.filter(user=user, status='completed').count()
        
        # Réservations récentes
        context['recent_reservations'] = Reservation.objects.filter(user=user).order_by('-start_time')[:5]
        
        return context

class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'users/profile_edit.html'
    form_class = UserUpdateForm
    
    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        messages.success(self.request, 'Votre profil a été mis à jour avec succès.')
        return reverse_lazy('users:profile')

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'users/password_change.html'
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy('users:password_change_done')

class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 10
    
    def test_func(self):
        return self.request.user.role == 'admin'
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # Recherche
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(city__icontains=search)
            )
        
        # Filtre par rôle
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filtre par statut
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['coach_users'] = User.objects.filter(role='coach').count()
        context['player_users'] = User.objects.filter(role='player').count()
        
        # Pourcentage calculées pour les barres de progression
        admin_count = User.objects.filter(role='admin').count()
        if context['total_users'] > 0:
            context['admin_percentage'] = (admin_count / context['total_users']) * 100
            context['active_percentage'] = (context['active_users'] / context['total_users']) * 100
            context['coach_percentage'] = (context['coach_users'] / context['total_users']) * 100
            context['player_percentage'] = (context['player_users'] / context['total_users']) * 100
        else:
            context['admin_percentage'] = 0
            context['active_percentage'] = 0
            context['coach_percentage'] = 0
            context['player_percentage'] = 0
        
        return context

class UserDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user'
    
    def test_func(self):
        return self.request.user.role == 'admin'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Réservations récentes
        if hasattr(user, 'reservations'):
            # Utiliser start_time car il existe sur le modèle Reservation
            context['recent_reservations'] = user.reservations.order_by('-start_time')[:5]
            
            # Statistiques réelles pour les cartes
            from reservations.models import Reservation
            from django.db.models import Sum, Avg, Count
            from django.utils import timezone
            from datetime import timedelta
            
            # Total des réservations
            context['total_reservations'] = user.reservations.count()
            
            # Total des dépenses
            total_spent = user.reservations.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            context['total_spent'] = total_spent
            
            # Fréquence moyenne par mois
            from django.db.models.functions import TruncMonth
            reservations_by_month = user.reservations.annotate(
                month=TruncMonth('start_time')
            ).values('month').annotate(
                count=Count('id')
            ).aggregate(
                avg_freq=Avg('count')
            )
            context['avg_frequency'] = round(reservations_by_month['avg_freq'] or 0, 1)
            
            # Statistiques supplémentaires
            context['confirmed_reservations'] = user.reservations.filter(
                status='confirmed'
            ).count()
            
            context['pending_reservations'] = user.reservations.filter(
                status='pending'
            ).count()
            
            # Réservations du mois en cours
            current_month = timezone.now().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            context['this_month_reservations'] = user.reservations.filter(
                start_time__gte=current_month
            ).count()
            
            # Dépenses du mois en cours
            this_month_spent = user.reservations.filter(
                start_time__gte=current_month
            ).aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            context['this_month_spent'] = this_month_spent
        
        return context

class UserEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    template_name = 'users/user_edit.html'
    form_class = UserUpdateForm
    
    def test_func(self):
        return self.request.user.role == 'admin'
    
    def get_success_url(self):
        messages.success(self.request, f'L\'utilisateur {self.object.get_full_name()} a été mis à jour.')
        return reverse_lazy('users:user_detail', kwargs={'pk': self.object.pk})

class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = User
    success_url = reverse_lazy('users:user_list')
    
    def test_func(self):
        return self.request.user.role == 'admin' and self.get_object() != self.request.user
    
    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            user_name = user.get_full_name()
            user_id = user.id
            
            # Supprimer avec SQL brut pour éviter les erreurs de transaction
            from django.db import connection
            
            with connection.cursor() as cursor:
                # Supprimer les logs d'audit
                cursor.execute("DELETE FROM audit_auditlog WHERE user_id = %s", [user_id])
                
                # Supprimer les tickets (via réservations)
                cursor.execute("""
                    DELETE FROM tickets_ticket 
                    WHERE reservation_id IN (
                        SELECT id FROM reservations_reservation WHERE user_id = %s
                    )
                """, [user_id])
                
                # Supprimer les paiements (via réservations)
                cursor.execute("""
                    DELETE FROM payments_payment 
                    WHERE reservation_id IN (
                        SELECT id FROM reservations_reservation WHERE user_id = %s
                    )
                """, [user_id])
                
                # Supprimer les réservations
                cursor.execute("DELETE FROM reservations_reservation WHERE user_id = %s", [user_id])
                
                # Supprimer les notifications
                cursor.execute("DELETE FROM notifications_notification WHERE recipient_id = %s", [user_id])
                
                # Supprimer les tokens d'authentification
                cursor.execute("DELETE FROM authtoken_token WHERE user_id = %s", [user_id])
                
                # Supprimer les préférences utilisateur
                cursor.execute("DELETE FROM users_userpreferences WHERE user_id = %s", [user_id])
                
                # Supprimer l'utilisateur
                cursor.execute("DELETE FROM users_user WHERE id = %s", [user_id])
            
            # Ajouter le message de succès
            messages.success(request, f'L\'utilisateur {user_name} a été supprimé.')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la suppression: {str(e)}')
        
        # Rediriger vers la liste
        return redirect(self.success_url)

@method_decorator(csrf_exempt, name='dispatch')
class UserToggleStatusView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    
    def test_func(self):
        return self.request.user.role == 'admin'
    
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        
        if user == request.user:
            return JsonResponse({'success': False, 'message': 'Vous ne pouvez pas modifier votre propre statut.'})
        
        activate = json.loads(request.body).get('activate', True)
        user.is_active = activate
        user.save()
        
        action = 'activé' if activate else 'désactivé'
        return JsonResponse({'success': True, 'message': f'Utilisateur {action} avec succès.'})

class UserReservationsView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    template_name = 'users/user_reservations.html'
    context_object_name = 'user'
    
    def test_func(self):
        return self.request.user.role == 'admin' or self.request.user == self.get_object()


@login_required
def change_password(request):
    """Vue pour changer le mot de passe utilisateur"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Vérifier que les mots de passe correspondent
        if new_password != confirm_password:
            messages.error(request, 'Les nouveaux mots de passe ne correspondent pas')
            return redirect('users:settings')
        
        # Vérifier l'ancien mot de passe
        if not request.user.check_password(old_password):
            messages.error(request, 'Ancien mot de passe incorrect')
            return redirect('users:settings')
        
        # Vérifier la force du mot de passe (minimum 8 caractères)
        if len(new_password) < 8:
            messages.error(request, 'Le mot de passe doit contenir au moins 8 caractères')
            return redirect('users:settings')
        
        # Changer le mot de passe
        request.user.set_password(new_password)
        request.user.save()
        
        # Forcer la reconnexion avec le nouveau mot de passe
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Mot de passe changé avec succès')
        return redirect('users:settings')
    
    return redirect('users:settings')


@login_required
def save_preferences(request):
    """Vue pour sauvegarder les préférences utilisateur"""
    if request.method == 'POST':
        try:
            # Récupérer ou créer les préférences de l'utilisateur
            preferences, created = UserPreferences.objects.get_or_create(
                user=request.user,
                defaults={
                    'language': 'fr',
                    'theme': 'light',
                    'timezone': 'Africa/Ndjamena',
                    'currency': 'XAF',
                    'email_notifications': True,
                    'sms_notifications': False,
                    'push_notifications': True,
                    'public_profile': True,
                    'show_email': True,
                    'show_phone': False,
                    'allow_friend_requests': True,
                    'data_analytics': False,
                }
            )
            
            # Mettre à jour les préférences avec les données du formulaire
            preferences.language = request.POST.get('language', preferences.language)
            preferences.theme = request.POST.get('theme', preferences.theme)
            preferences.timezone = request.POST.get('timezone', preferences.timezone)
            preferences.currency = request.POST.get('currency', preferences.currency)
            
            # Notifications
            preferences.email_notifications = request.POST.get('emailNotifications') == 'on'
            preferences.sms_notifications = request.POST.get('smsNotifications') == 'on'
            preferences.push_notifications = request.POST.get('pushNotifications') == 'on'
            
            # Confidentialité
            preferences.public_profile = request.POST.get('publicProfile') == 'on'
            preferences.show_email = request.POST.get('showEmail') == 'on'
            preferences.show_phone = request.POST.get('showPhone') == 'on'
            preferences.allow_friend_requests = request.POST.get('allowFriendRequests') == 'on'
            preferences.data_analytics = request.POST.get('dataAnalytics') == 'on'
            
            preferences.save()
            
            messages.success(request, 'Vos préférences ont été enregistrées avec succès!')
            
        except Exception as e:
            messages.error(request, 'Une erreur est survenue lors de la sauvegarde des préférences.')
            print(f"Erreur préférences: {e}")
    
    return redirect('users:settings')


@login_required
def settings_view(request):
    """Vue simple pour les paramètres utilisateur"""
    # Récupérer ou créer les préférences de l'utilisateur
    preferences, created = UserPreferences.objects.get_or_create(
        user=request.user,
        defaults={
            'language': 'fr',
            'theme': 'light',
            'timezone': 'Africa/Ndjamena',
            'currency': 'XAF',
            'email_notifications': True,
            'sms_notifications': False,
            'push_notifications': True,
            'public_profile': True,
            'show_email': True,
            'show_phone': False,
            'allow_friend_requests': True,
            'data_analytics': False,
        }
    )
    
    # Calculer les vraies statistiques du compte
    user = request.user
    
    # Complétude du profil (sur 100%)
    profile_fields = [
        user.first_name, user.last_name, user.phone, 
        user.date_of_birth, user.city, user.country,
        user.address, user.postal_code
    ]
    filled_fields = sum(1 for field in profile_fields if field)
    profile_completeness = (filled_fields / len(profile_fields)) * 100
    
    # Score de sécurité (sur 100%)
    security_score = 0
    if user.password and len(user.password) > 8:
        security_score += 30
    if user.email:
        security_score += 20
    if hasattr(user, 'email_verified') and user.email_verified:
        security_score += 25
    if hasattr(user, 'two_factor_enabled') and user.two_factor_enabled:
        security_score += 25
    
    # Score de confidentialité (sur 100%)
    privacy_score = 0
    if hasattr(preferences, 'public_profile') and not preferences.public_profile:
        privacy_score += 30
    if hasattr(preferences, 'show_email') and not preferences.show_email:
        privacy_score += 20
    if hasattr(preferences, 'show_phone') and not preferences.show_phone:
        privacy_score += 20
    if hasattr(preferences, 'data_analytics') and not preferences.data_analytics:
        privacy_score += 30
    
    # Score global
    overall_score = (profile_completeness + security_score + privacy_score) / 3
    
    # Note de sécurité (A+, A, B, C, D)
    if security_score >= 90:
        security_grade = "A+"
    elif security_score >= 80:
        security_grade = "A"
    elif security_score >= 70:
        security_grade = "B"
    elif security_score >= 60:
        security_grade = "C"
    else:
        security_grade = "D"
    
    context = {
        'preferences': preferences,
        'profile_completeness': round(profile_completeness),
        'security_score': round(security_score),
        'privacy_score': round(privacy_score),
        'overall_score': round(overall_score),
        'security_grade': security_grade,
    }
    
    return render(request, 'profile/parametres.html', context)


@login_required
def api_preferences(request):
    """API pour récupérer les préférences utilisateur (pour le thème)"""
    try:
        preferences, created = UserPreferences.objects.get_or_create(
            user=request.user,
            defaults={
                'language': 'fr',
                'theme': 'light',
                'timezone': 'Africa/Ndjamena',
                'currency': 'XAF',
            }
        )
        
        return JsonResponse({
            'theme': preferences.theme,
            'language': preferences.language,
            'timezone': preferences.timezone,
            'currency': preferences.currency,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def set_language(request):
    """Vue pour changer la langue de l'utilisateur"""
    if request.method == 'POST':
        language = request.POST.get('language', 'fr')
        
        # Valider que la langue est supportée
        from django.conf import settings
        if language not in [lang[0] for lang in settings.LANGUAGES]:
            language = 'fr'
        
        # Mettre à jour les préférences utilisateur
        try:
            preferences, created = UserPreferences.objects.get_or_create(
                user=request.user,
                defaults={'language': language}
            )
            preferences.language = language
            preferences.save()
            
            # Activer la langue pour la session
            from django.utils import translation
            translation.activate(language)
            request.session['_language'] = language  # Clé correcte pour Django
            
            # Retourner JSON pour le JavaScript
            return JsonResponse({'success': True, 'language': language})
            
        except Exception as e:
            print(f"Erreur changement langue: {e}")  # Debug
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})
