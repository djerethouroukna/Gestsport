from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Crée automatiquement un profil utilisateur lors de la création d'un utilisateur."""
    if created:
        # Vous pouvez ajouter ici des actions à effectuer lors de la création d'un utilisateur
        pass

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Sauvegarde le profil utilisateur lors de la sauvegarde de l'utilisateur."""
    # Vous pouvez ajouter ici des actions à effectuer lors de la mise à jour d'un utilisateur
    pass