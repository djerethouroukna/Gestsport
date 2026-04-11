# terrains/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class TerrainStatus(models.TextChoices):
    AVAILABLE = 'available', _('Disponible')
    MAINTENANCE = 'maintenance', _('En maintenance')
    CLOSED = 'closed', _('Fermé')

class TerrainType(models.TextChoices):
    FOOTBALL = 'football', _('Football')
    TENNIS = 'tennis', _('Tennis')
    BASKETBALL = 'basketball', _('Basketball')
    VOLLEYBALL = 'volleyball', _('Volleyball')
    HANDBALL = 'handball', _('Handball')

class Equipment(models.Model):
    """Équipements disponibles pour les terrains"""
    class Meta:
        verbose_name = _('équipement')
        verbose_name_plural = _('équipements')
        ordering = ['name']

    name = models.CharField(_('nom'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    icon = models.CharField(_('icône'), max_length=50, help_text=_('Classe Font Awesome'))
    
    def __str__(self):
        return self.name

class Terrain(models.Model):
    class Meta:
        verbose_name = _('terrain')
        verbose_name_plural = _('terrains')
        ordering = ['name']

    name = models.CharField(_('nom'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    terrain_type = models.CharField(
        _('type de terrain'),
        max_length=20,
        choices=TerrainType.choices
    )
    capacity = models.PositiveIntegerField(_('capacité'))
    price_per_hour = models.DecimalField(
        _('prix par heure'),
        max_digits=10,
        decimal_places=2
    )
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=TerrainStatus.choices,
        default=TerrainStatus.AVAILABLE
    )
    image = models.URLField(
        _('image principale'),
        max_length=500,
        blank=True,
        null=True,
        help_text=_('URL de l\'image principale du terrain')
    )

    # Coordonnées géographiques (optionnelles)
    latitude = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('Latitude du terrain (ex: 48.8566)')
    )
    longitude = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('Longitude du terrain (ex: 2.3522)')
    )

    average_rating = models.DecimalField(
        _('note moyenne'),
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_terrain_type_display()})"
    
    def update_average_rating(self):
        """Met à jour la note moyenne du terrain"""
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.average_rating = round(avg, 2)
        else:
            self.average_rating = 0
        self.save(update_fields=['average_rating'])

class TerrainPhoto(models.Model):
    """Photos multiples pour les terrains"""
    class Meta:
        verbose_name = _('photo de terrain')
        verbose_name_plural = _('photos de terrain')
        ordering = ['order']

    terrain = models.ForeignKey(
        Terrain,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name=_('terrain')
    )
    image = models.ImageField(
        _('image'),
        upload_to='terrain_photos/'
    )
    caption = models.CharField(_('légende'), max_length=200, blank=True)
    order = models.PositiveIntegerField(_('ordre'), default=0)
    is_primary = models.BooleanField(_('photo principale'), default=False)
    created_at = models.DateTimeField(_('date d\'ajout'), auto_now_add=True)

    def __str__(self):
        return f"Photo de {self.terrain.name} - {self.caption or self.order}"

class TerrainEquipment(models.Model):
    """Équipements disponibles pour un terrain spécifique"""
    class Meta:
        verbose_name = _('équipement de terrain')
        verbose_name_plural = _('équipements de terrain')
        unique_together = ['terrain', 'equipment']

    CONDITION_CHOICES = [
        ('excellent', _('Excellent')),
        ('good', _('Bon')),
        ('fair', _('Moyen')),
        ('poor', _('Mauvais')),
    ]

    terrain = models.ForeignKey(
        Terrain,
        on_delete=models.CASCADE,
        related_name='terrain_equipments',
        verbose_name=_('terrain')
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        verbose_name=_('équipement')
    )
    quantity = models.PositiveIntegerField(_('quantité'), default=1)
    condition = models.CharField(
        _('état'),
        max_length=20,
        choices=CONDITION_CHOICES,
        default='good'
    )
    
    def __str__(self):
        return f"{self.terrain.name} - {self.equipment.name} ({self.quantity})"

class OpeningHours(models.Model):
    """Horaires d'ouverture des terrains"""
    class Meta:
        verbose_name = _('horaire d\'ouverture')
        verbose_name_plural = _('horaires d\'ouverture')
        unique_together = ['terrain', 'day_of_week']
        ordering = ['day_of_week', 'opening_time']

    WEEKDAYS = [
        (0, _('Lundi')),
        (1, _('Mardi')),
        (2, _('Mercredi')),
        (3, _('Jeudi')),
        (4, _('Vendredi')),
        (5, _('Samedi')),
        (6, _('Dimanche')),
    ]

    terrain = models.ForeignKey(
        Terrain,
        on_delete=models.CASCADE,
        related_name='opening_hours',
        verbose_name=_('terrain')
    )
    day_of_week = models.PositiveIntegerField(_('jour de la semaine'), choices=WEEKDAYS)
    opening_time = models.TimeField(_('heure d\'ouverture'))
    closing_time = models.TimeField(_('heure de fermeture'))
    is_closed = models.BooleanField(_('fermé'), default=False)

    def __str__(self):
        day_name = dict(self.WEEKDAYS).get(self.day_of_week)
        if self.is_closed:
            return f"{self.terrain.name} - {day_name}: Fermé"
        return f"{self.terrain.name} - {day_name}: {self.opening_time} à {self.closing_time}"

class MaintenancePeriod(models.Model):
    """Périodes de maintenance des terrains"""
    class Meta:
        verbose_name = _('période de maintenance')
        verbose_name_plural = _('périodes de maintenance')
        ordering = ['start_date']

    terrain = models.ForeignKey(
        Terrain,
        on_delete=models.CASCADE,
        related_name='maintenance_periods',
        verbose_name=_('terrain')
    )
    start_date = models.DateTimeField(_('date de début'))
    end_date = models.DateTimeField(_('date de fin'))
    reason = models.TextField(_('raison'), blank=True)
    is_active = models.BooleanField(_('active'), default=True)

    def __str__(self):
        return f"Maintenance {self.terrain.name}: {self.start_date} à {self.end_date}"

class Review(models.Model):
    """Avis et notes des utilisateurs sur les terrains"""
    class Meta:
        verbose_name = _('avis')
        verbose_name_plural = _('avis')
        unique_together = ['terrain', 'user']
        ordering = ['-created_at']

    terrain = models.ForeignKey(
        Terrain,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('terrain')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('utilisateur')
    )
    rating = models.PositiveIntegerField(
        _('note'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(_('commentaire'), blank=True)
    is_approved = models.BooleanField(_('approuvé'), default=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Avis de {self.user.get_full_name()} pour {self.terrain.name}: {self.rating}/5"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.terrain.update_average_rating()
