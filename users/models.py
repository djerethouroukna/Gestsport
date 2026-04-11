from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """Définit un gestionnaire pour le modèle User sans le champ 'username'."""
    
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Crée et enregistre un utilisateur avec l'email et le mot de passe fournis."""
        if not email:
            raise ValueError('Les utilisateurs doivent avoir une adresse email')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Crée et enregistre un utilisateur régulier avec l'email et le mot de passe fournis."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Crée et enregistre un superutilisateur avec l'email et le mot de passe fournis."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)  # Rôle admin par défaut

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Modèle d'utilisateur personnalisé utilisant l'email comme identifiant."""
    
    class Role(models.TextChoices):
        PLAYER = 'player', _('Joueur')
        COACH = 'coach', _('Entraîneur')
        ADMIN = 'admin', _('Administrateur')
    
    username = None
    email = models.EmailField(_('adresse email'), unique=True)
    first_name = models.CharField(_('prénom'), max_length=30, blank=True)
    last_name = models.CharField(_('nom'), max_length=30, blank=True)
    role = models.CharField(
        _('rôle'),
        max_length=10,
        choices=Role.choices,
        default=Role.PLAYER
    )
    phone = models.CharField(_('téléphone'), max_length=20, blank=True)
    date_of_birth = models.DateField(_('date de naissance'), null=True, blank=True)
    address = models.TextField(_('adresse'), blank=True)
    city = models.CharField(_('ville'), max_length=100, blank=True)
    postal_code = models.CharField(_('code postal'), max_length=10, blank=True)
    country = models.CharField(_('pays'), max_length=100, blank=True)
    profile_picture = models.ImageField(
        _('photo de profil'),
        upload_to='profile_pics/',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(_('actif'), default=True)
    date_joined = models.DateTimeField(_('date d\'inscription'), auto_now_add=True)
    last_updated = models.DateTimeField(_('dernière mise à jour'), auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = _('utilisateur')
        verbose_name_plural = _('utilisateurs')
        ordering = ['-date_joined']

    def __str__(self):
        return self.get_full_name() or self.email

    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """Retourne le prénom de l'utilisateur."""
        return self.first_name

    def get_initials(self):
        """Retourne les initiales de l'utilisateur."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        elif self.email:
            return self.email[0].upper()
        return "U"

    @property
    def is_player(self):
        return self.role == self.Role.PLAYER

    @property
    def is_coach(self):
        return self.role == self.Role.COACH

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN


class UserPreferences(models.Model):
    """Préférences utilisateur pour personnaliser l'expérience"""
    
    class Theme(models.TextChoices):
        LIGHT = 'light', _('Clair')
        DARK = 'dark', _('Sombre')
        AUTO = 'auto', _('Automatique')
    
    class Language(models.TextChoices):
        FRENCH = 'fr', _('Français')
        ENGLISH = 'en', _('English')
        SPANISH = 'es', _('Español')
        ARABIC = 'ar', _('العربية')
    
    class Currency(models.TextChoices):
        XAF = 'XAF', _('FCFA')
        FCFA = 'FCFA', _('FCFA')
        USD = 'USD', _('Dollar')
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='preferences',
        verbose_name=_('Utilisateur')
    )
    
    # Interface
    language = models.CharField(
        max_length=10, 
        choices=Language.choices, 
        default=Language.FRENCH,
        verbose_name=_('Langue')
    )
    theme = models.CharField(
        max_length=10, 
        choices=Theme.choices, 
        default=Theme.LIGHT,
        verbose_name=_('Thème')
    )
    timezone = models.CharField(
        max_length=50, 
        default='Africa/Ndjamena',
        verbose_name=_('Fuseau horaire')
    )
    currency = models.CharField(
        max_length=4, 
        choices=Currency.choices, 
        default=Currency.XAF,
        verbose_name=_('Devise')
    )
    
    # Notifications
    email_notifications = models.BooleanField(
        default=True, 
        verbose_name=_('Notifications par email')
    )
    sms_notifications = models.BooleanField(
        default=False, 
        verbose_name=_('Notifications par SMS')
    )
    push_notifications = models.BooleanField(
        default=True, 
        verbose_name=_('Notifications push')
    )
    
    # Confidentialité
    public_profile = models.BooleanField(
        default=True, 
        verbose_name=_('Profil public')
    )
    show_email = models.BooleanField(
        default=True, 
        verbose_name=_('Afficher email dans profil')
    )
    show_phone = models.BooleanField(
        default=False, 
        verbose_name=_('Afficher téléphone dans profil')
    )
    allow_friend_requests = models.BooleanField(
        default=True, 
        verbose_name=_('Autoriser demandes d\'amis')
    )
    data_analytics = models.BooleanField(
        default=False, 
        verbose_name=_('Participer aux analytics')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name=_('Créé le')
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name=_('Mis à jour le')
    )
    
    class Meta:
        verbose_name = _('Préférences utilisateur')
        verbose_name_plural = _('Préférences utilisateurs')
    
    def __str__(self):
        return f"Préférences de {self.user.email}"
    
    def get_theme_display_short(self):
        """Retourne l'affichage court du thème"""
        return dict(self.Theme.choices).get(self.theme, self.theme)
    
    def get_language_display_short(self):
        """Retourne l'affichage court de la langue"""
        return dict(self.Language.choices).get(self.language, self.language)
    
    def get_currency_display_short(self):
        """Retourne l'affichage court de la devise"""
        return dict(self.Currency.choices).get(self.currency, self.currency)