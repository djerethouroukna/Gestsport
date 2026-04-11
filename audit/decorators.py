from functools import wraps
from .models import AuditLog
from .middleware import get_current_user, get_current_ip, get_current_user_agent


def audit_action(action, model_name=None, get_object_repr=None, metadata=None):
    """
    Décorateur pour logger les actions personnalisées
    
    Usage:
    @audit_action('EXPORT', 'Reservation', lambda obj: f"Export {obj.id}")
    def export_reservation(request, pk):
        pass
    """
    def decorator(func):
        @wraps(func)
        def wrapped_view(request, *args, **kwargs):
            # Exécuter la fonction originale
            result = func(request, *args, **kwargs)
            
            try:
                # Récupérer l'objet si possible
                obj = None
                if hasattr(result, '__iter__') and not isinstance(result, str):
                    # Si c'est un queryset ou une liste, prendre le premier élément
                    obj = next(iter(result), None)
                elif hasattr(result, 'pk'):
                    # Si c'est un modèle Django
                    obj = result
                elif 'pk' in kwargs:
                    # Essayer de récupérer depuis les kwargs
                    from django.apps import apps
                    try:
                        model_class = apps.get_model('reservations', model_name or 'Reservation')
                        obj = model_class.objects.get(pk=kwargs['pk'])
                    except:
                        pass
                
                # Déterminer la représentation de l'objet
                object_repr = ''
                object_id = None
                if obj:
                    object_repr = str(obj)[:200]
                    object_id = obj.pk if hasattr(obj, 'pk') else None
                elif get_object_repr:
                    object_repr = get_object_repr(request, *args, **kwargs)[:200]
                
                # Créer le log d'audit
                AuditLog.objects.create(
                    user=get_current_user(),
                    action=action,
                    model_name=model_name or 'Custom',
                    object_id=object_id,
                    object_repr=object_repr,
                    metadata=metadata or {},
                    ip_address=get_current_ip(),
                    user_agent=get_current_user_agent()
                )
                
            except Exception as e:
                # Ne jamais échouer l'action à cause d'un log
                print(f"Erreur dans le décorateur d'audit: {e}")
            
            return result
        return wrapped_view
    return decorator


def sensitive_operation(description="Opération sensible"):
    """
    Décorateur pour marquer des opérations comme sensibles
    """
    def decorator(func):
        @wraps(func)
        def wrapped_view(request, *args, **kwargs):
            try:
                # Logger l'opération sensible
                AuditLog.objects.create(
                    user=get_current_user(),
                    action='SENSITIVE_OPERATION',
                    model_name='Security',
                    object_repr=description,
                    metadata={
                        'function': func.__name__,
                        'module': func.__module__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    },
                    ip_address=get_current_ip(),
                    user_agent=get_current_user_agent()
                )
            except Exception as e:
                print(f"Erreur dans le décorateur sensible: {e}")
            
            return func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def log_view_action(action='VIEW'):
    """
    Décorateur simple pour logger les consultations de pages
    """
    def decorator(func):
        @wraps(func)
        def wrapped_view(request, *args, **kwargs):
            try:
                # Logger la consultation de page
                AuditLog.objects.create(
                    user=get_current_user(),
                    action=action,
                    model_name='Page',
                    object_repr=f"{func.__module__}.{func.__name__}",
                    metadata={
                        'path': request.path,
                        'method': request.method,
                        'get_params': dict(request.GET)
                    },
                    ip_address=get_current_ip(),
                    user_agent=get_current_user_agent()
                )
            except Exception as e:
                # Ignorer les erreurs de logging pour ne pas perturber l'UX
                pass
            
            return func(request, *args, **kwargs)
        return wrapped_view
    return decorator
