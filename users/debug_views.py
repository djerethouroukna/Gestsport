from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.views.generic import FormView
from django.contrib.auth.forms import PasswordResetForm

User = get_user_model()

class DebugPasswordResetView(FormView):
    template_name = 'users/password_reset.html'
    form_class = PasswordResetForm
    success_url = '/users/password-reset/done/'

    def form_valid(self, form):
        # Debug: Afficher les données du formulaire
        email = form.cleaned_data['email']
        print(f"🔍 DEBUG: Email saisi = '{email}'")
        
        # Chercher l'utilisateur
        try:
            user = User.objects.get(email=email)
            print(f"✅ DEBUG: Utilisateur trouvé - ID: {user.id}, Email: '{user.email}'")
            
            # Générer les tokens
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            
            print(f"🔧 DEBUG: UIDB64 = '{uidb64}'")
            print(f"🔧 DEBUG: Token = '{token}'")
            
            # Contexte pour l'email
            context = {
                'user': user,
                'domain': '127.0.0.1:8000',
                'protocol': 'http',
                'uidb64': uidb64,
                'token': token,
                'site_name': 'GestSport'
            }
            
            # Rendre le template d'email
            email_content = render_to_string('users/password_reset_email.html', context)
            print(f"📧 DEBUG: Contenu email généré")
            
            # Envoyer l'email (en mode console pour le debug)
            subject = settings.EMAIL_SUBJECT_PREFIX + "Réinitialisation du mot de passe"
            email = EmailMultiAlternatives(
                subject,
                email_content,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            
            try:
                email.send()
                print(f"✅ DEBUG: Email envoyé à {user.email}")
            except Exception as e:
                print(f"❌ DEBUG: Erreur envoi email: {e}")
                
        except User.DoesNotExist:
            print(f"❌ DEBUG: Utilisateur non trouvé pour l'email '{email}'")
            # Ne pas révéler que l'utilisateur n'existe pas (sécurité)
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        print(f"❌ DEBUG: Formulaire invalide")
        print(f"❌ DEBUG: Erreurs: {form.errors}")
        return super().form_invalid(form)
