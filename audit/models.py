from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditLog(models.Model):
    """Modèle pour enregistrer toutes les actions des utilisateurs"""
    
    # Qui a fait l'action
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Utilisateur"
    )
    
    # Quelle action
    ACTION_CHOICES = [
        ('CREATE', 'Création'),
        ('UPDATE', 'Modification'),
        ('DELETE', 'Suppression'),
        ('LOGIN', 'Connexion'),
        ('LOGOUT', 'Déconnexion'),
        ('VIEW', 'Consultation'),
        ('EXPORT', 'Export'),
        ('SCAN', 'Scan Ticket'),
        ('FAILED_LOGIN', 'Connexion échouée'),
        ('PASSWORD_CHANGE', 'Changement mot de passe'),
        ('PERMISSION_CHANGE', 'Changement permissions'),
    ]
    action = models.CharField(
        max_length=20, 
        choices=ACTION_CHOICES,
        verbose_name="Action"
    )
    
    # Sur quel objet
    model_name = models.CharField(
        max_length=100, 
        db_index=True,
        verbose_name="Modèle"
    )
    object_id = models.PositiveIntegerField(
        null=True, 
        blank=True,
        db_index=True,
        verbose_name="ID de l'objet"
    )
    object_repr = models.CharField(
        max_length=200, 
        verbose_name="Représentation de l'objet"
    )
    
    # Détails de l'action
    changes = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name="Changements"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True, 
        db_index=True,
        verbose_name="Date/Heure"
    )
    
    # Contexte technique
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name="Adresse IP"
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )
    
    # Métadonnées supplémentaires
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name="Métadonnées"
    )
    
    class Meta:
        verbose_name = "Log d'audit"
        verbose_name_plural = "Logs d'audit"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['model_name', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.email if self.user else "Système"
        return f"{user_str} - {self.action} - {self.model_name} - {self.timestamp}"
    
    @property
    def action_display(self):
        """Retourne le libellé de l'action"""
        return dict(self.ACTION_CHOICES).get(self.action, self.action)
