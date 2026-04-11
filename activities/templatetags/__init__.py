from django import template

register = template.Library()

@register.filter
def status_color(status):
    """Retourne la classe Bootstrap de couleur selon le statut"""
    colors = {
        'pending': 'warning',
        'confirmed': 'success', 
        'completed': 'secondary',
        'cancelled': 'danger'
    }
    return colors.get(status, 'secondary')
