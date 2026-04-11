from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label=_('Adresse email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'harouna@email.com',
            'required': True
        })
    )
    
    password1 = forms.CharField(
        label=_('Mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        }),
        help_text=_('Le mot de passe doit contenir au moins 8 caractères.')
    )
    
    password2 = forms.CharField(
        label=_('Confirmer le mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        })
    )
    
    remember_me = forms.BooleanField(
        label=_('Se souvenir de moi'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ('email', 'password1', 'password2', 'remember_me')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'autofocus': True})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('Un compte avec cet email existe déjà.'))
        return email


class PublicRegistrationForm(forms.ModelForm):
    """Formulaire d'inscription publique pour les joueurs uniquement"""
    password1 = forms.CharField(
        label=_('Mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        }),
        help_text=_('Le mot de passe doit contenir au moins 8 caractères.')
    )
    
    password2 = forms.CharField(
        label=_('Confirmer le mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        })
    )
    
    terms_accepted = forms.BooleanField(
        label=_("J'accepte les conditions d'utilisation"),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'password1', 'password2',
            'phone', 'date_of_birth', 'address', 'postal_code',
            'city', 'country', 'profile_picture', 'terms_accepted'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Zèbre',
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'harouna',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'harouna@email.com',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+235 60 00 00 00',
                'required': True
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '123 rue de la République',
                'required': True
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '12345',
                'required': True
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'N\'Djamena',
                'required': True
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tchad',
                'required': True
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update({'autofocus': True})
        
        # Le rôle est automatiquement défini à 'player' et n'est pas affiché
        # Les joueurs peuvent s'inscrire librement

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('Un compte avec cet email existe déjà.'))
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError(_("Les mots de passe ne correspondent pas."))
        
        if len(password1) < 8:
            raise ValidationError(_("Le mot de passe doit contenir au moins 8 caractères."))
        
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = 'player'  # Rôle par défaut pour les inscriptions publiques
        user.is_active = True  # Approbation automatique
        user.email_verified = False  # Nécessite validation email
        
        if commit:
            user.save()
            # Envoyer email de validation
            self.send_verification_email(user)
        
        return user
    
    def send_verification_email(self, user):
        """Envoyer un email de validation"""
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Générer le token de validation
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # URL de validation
        verification_url = f"http://127.0.0.1:8000/users/verify-email/{uid}/{token}/"
        
        # Préparer le contexte
        context = {
            'user': user,
            'verification_url': verification_url,
        }
        
        # Rendre les templates HTML et texte
        html_content = render_to_string('emails/email_verification.html', context)
        text_content = f"""
        Bonjour {user.first_name} {user.last_name},
        
        Merci de vous être inscrit sur GestSport !
        
        Pour activer votre compte, veuillez cliquer sur le lien suivant :
        {verification_url}
        
        Ce lien expirera dans 24 heures.
        
        Cordialement,
        L'équipe GestSport
        """
        
        # Créer l'email avec HTML et texte
        subject = settings.EMAIL_SUBJECT_PREFIX + "Vérification de votre compte GestSport"
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            print(f"✅ Email de vérification envoyé à {user.email}")
        except Exception as e:
            print(f"❌ Erreur lors de l'envoi de l'email: {e}")


class CustomRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_('Mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        }),
        help_text=_('Le mot de passe doit contenir au moins 8 caractères.')
    )
    
    password2 = forms.CharField(
        label=_('Confirmer le mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        })
    )
    
    terms_accepted = forms.BooleanField(
        label=_("J'accepte les conditions d'utilisation"),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'password1', 'password2',
            'role', 'phone', 'date_of_birth', 'address', 'postal_code',
            'city', 'country', 'profile_picture', 'terms_accepted', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Zèbre',
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'harouna',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'harouna@email.com',
                'required': True
            }),
            'role': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+235 60 00 00 00'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '123 rue de la République'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '75001'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'N\'Djaména'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tchad'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Récupérer l'utilisateur connecté
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update({'autofocus': True})
        
        # Restreindre les choix de rôle selon l'utilisateur connecté
        if self.user and self.user.role == 'player':
            # Les joueurs ne peuvent pas créer de comptes
            raise ValidationError(_("Les joueurs ne peuvent pas créer de comptes."))
        elif self.user and self.user.role == 'coach':
            # Les coachs ne peuvent pas créer de comptes
            raise ValidationError(_("Les entraîneurs ne peuvent pas créer de comptes."))
        elif not self.user or not self.user.is_authenticated:
            # Utilisateur non connecté : ne peut pas créer de compte
            raise ValidationError(_(
                "Seuls les administrateurs peuvent créer des comptes. "
                "Veuillez contacter un administrateur pour créer un compte."
            ))
        # Si admin : tous les choix sont disponibles

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('Un compte avec cet email existe déjà.'))
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError(_("Les mots de passe ne correspondent pas."))
        return password2

    def clean_role(self):
        role = self.cleaned_data.get('role')
        user = self.user
        
        # Seuls les admins peuvent créer des comptes
        if not user or user.role != 'admin':
            raise ValidationError(_("Seuls les administrateurs peuvent créer des comptes."))
        
        return role

    def save(self, commit=True):
        new_user = super().save(commit=False)
        new_user.set_password(self.cleaned_data['password1'])
        
        # Si un non-admin crée un compte coach, le désactiver par défaut
        creator = self.user
        if not creator or not creator.is_authenticated or creator.role != 'admin':
            if self.cleaned_data.get('role') == 'coach':
                new_user.is_active = False
                
        if commit:
            new_user.save()
        return new_user


class AdminUserCreationForm(CustomRegistrationForm):
    """Formulaire utilisé par les admins pour créer des comptes"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pour les admins, le champ rôle est entièrement disponible
        self.fields['role'].widget.attrs.pop('disabled', None)
        
        # Définir la valeur initiale pour is_active
        self.fields['is_active'].initial = True
    
    def clean_role(self):
        # Les admins peuvent créer n'importe quel type de compte
        return self.cleaned_data.get('role')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = self.cleaned_data.get('is_active', True)
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'date_of_birth',
            'address', 'postal_code', 'city', 'country', 'profile_picture'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Zèbre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'harouna'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'harouna@email.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+235 60 00 00 00'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '123 rue de la République'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '75001'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'N\'Djaména'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tchad'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update({'autofocus': True})


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label=_('Mot de passe actuel'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        })
    )
    
    new_password1 = forms.CharField(
        label=_('Nouveau mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        }),
        help_text=_('Le mot de passe doit contenir au moins 8 caractères.')
    )
    
    new_password2 = forms.CharField(
        label=_('Confirmer le nouveau mot de passe'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
            'required': True
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'autofocus': True})
