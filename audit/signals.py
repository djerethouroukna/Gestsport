from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
import json

from .models import AuditLog
from .middleware import get_current_user, get_current_ip, get_current_user_agent


def get_model_changes(old_instance, new_instance):
    """
    Compare deux instances de modèle et retourne les changements
    """
    changes = {}
    
    # Récupérer tous les champs du modèle
    for field in old_instance._meta.fields:
        field_name = field.name
        
        # Ignorer certains champs sensibles
        if field_name in ['password', 'last_login', 'modified_at']:
            continue
            
        old_value = getattr(old_instance, field_name)
        new_value = getattr(new_instance, field_name)
        
        # Gérer les objets ForeignKey
        if hasattr(old_value, '__str__'):
            old_value = str(old_value)
        if hasattr(new_value, '__str__'):
            new_value = str(new_value)
            
        # Gérer les dates
        if hasattr(old_value, 'isoformat'):
            old_value = old_value.isoformat()
        if hasattr(new_value, 'isoformat'):
            new_value = new_value.isoformat()
            
        if old_value != new_value:
            changes[field_name] = {
                'old': old_value,
                'new': new_value
            }
    
    return changes


def create_audit_log(action, model_name, instance, user=None, changes=None, metadata=None):
    """
    Crée un log d'audit avec les informations fournies
    """
    try:
        # Récupérer l'utilisateur depuis différentes sources
        if not user:
            user = get_current_user()
        
        # Créer le log
        audit_log = AuditLog.objects.create(
            user=user,
            action=action,
            model_name=model_name,
            object_id=instance.pk if instance else None,
            object_repr=str(instance)[:200] if instance else '',
            changes=changes or {},
            ip_address=get_current_ip(),
            user_agent=get_current_user_agent(),
            metadata=metadata or {}
        )
        return audit_log
    except Exception as e:
        # Ne jamais échouer une opération à cause d'un log d'audit
        print(f"Erreur lors de la création du log d'audit: {e}")
        return None


@receiver(post_save)
def log_save_action(sender, instance, created, **kwargs):
    """
    Signal déclenché lors de la création ou modification d'un objet
    """
    # Ignorer les logs eux-mêmes pour éviter boucle infinie
    if sender.__name__ == 'AuditLog':
        return
    
    # Ignorer les modèles non critiques ou système
    ignored_models = [
        'Session', 'MigrationHistory', 'LogEntry', 'Notification',
        'ContentType', 'Permission', 'Group', 'Message'
    ]
    if sender.__name__ in ignored_models:
        return
    
    # Ignorer les mises à jour de champs automatiques
    if not created:
        # Vérifier si seuls les champs automatiques ont changé
        auto_fields = ['modified_at', 'updated_at', 'last_login']
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            changes = get_model_changes(old_instance, instance)
            
            # Filtrer les changements pour ne garder que les champs significatifs
            significant_changes = {
                k: v for k, v in changes.items() 
                if k not in auto_fields
            }
            
            # Si aucun changement significatif, ne pas logger
            if not significant_changes:
                return
                
            changes = significant_changes
        except ObjectDoesNotExist:
            # Impossible de récupérer l'ancienne version
            changes = {'note': 'Ancienne version non disponible'}
    else:
        changes = {}
    
    action = 'CREATE' if created else 'UPDATE'
    
    create_audit_log(
        action=action,
        model_name=sender.__name__,
        instance=instance,
        changes=changes
    )


@receiver(post_delete)
def log_delete_action(sender, instance, **kwargs):
    """
    Signal déclenché lors de la suppression d'un objet
    """
    # Ignorer les logs eux-mêmes
    if sender.__name__ == 'AuditLog':
        return
    
    # Ignorer les modèles non critiques ou système
    ignored_models = [
        'Session', 'MigrationHistory', 'LogEntry', 'Notification',
        'ContentType', 'Permission', 'Group', 'Message'
    ]
    if sender.__name__ in ignored_models:
        return
    
    create_audit_log(
        action='DELETE',
        model_name=sender.__name__,
        instance=instance,
        changes={'deleted': True}
    )


@receiver(user_logged_in)
def log_login(sender, user, request, **kwargs):
    """
    Signal déclenché lors de la connexion réussie d'un utilisateur
    """
    create_audit_log(
        action='LOGIN',
        model_name='User',
        instance=user,
        user=user,
        metadata={
            'login_successful': True,
            'session_key': request.session.session_key
        }
    )


@receiver(user_logged_out)
def log_logout(sender, user, request, **kwargs):
    """
    Signal déclenché lors de la déconnexion d'un utilisateur
    """
    create_audit_log(
        action='LOGOUT',
        model_name='User',
        instance=user,
        user=user,
        metadata={
            'logout_successful': True
        }
    )


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """
    Signal déclenché lors d'une tentative de connexion échouée
    """
    username = credentials.get('username', 'inconnu')
    
    create_audit_log(
        action='FAILED_LOGIN',
        model_name='User',
        instance=None,
        user=None,
        metadata={
            'username_attempted': username,
            'failure_reason': 'Invalid credentials'
        }
    )
