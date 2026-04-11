# reservations/admin_custom.py - Admin personnalisé avec dashboard pour réservations expirées
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q

from .models import Reservation, ReservationStatus


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """Admin personnalisé pour les réservations avec dashboard"""
    
    list_display = (
        'user_info', 'terrain_info', 'datetime_info', 
        'status_badge', 'ticket_info', 'actions_column'
    )
    
    list_filter = (
        'status', 'terrain', 'start_time', 'end_time',
        ('start_time', admin.DateFieldListFilter),
    )
    
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'terrain__name', 'ticket__ticket_number'
    )
    
    ordering = ('-start_time',)
    
    def get_queryset(self, request):
        """Optimiser les requêtes"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'terrain', 'ticket_set')
    
    def user_info(self, obj):
        """Afficher les infos utilisateur"""
        if obj.user:
            name = obj.user.get_full_name() or obj.user.email
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                name, obj.user.email
            )
        return '-'
    user_info.short_description = 'Utilisateur'
    
    def terrain_info(self, obj):
        """Afficher les infos terrain"""
        if obj.terrain:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.terrain.name, obj.terrain.terrain_type
            )
        return '-'
    terrain_info.short_description = 'Terrain'
    
    def datetime_info(self, obj):
        """Afficher les infos de date/heure"""
        start = obj.start_time.strftime('%d/%m %H:%M')
        end = obj.end_time.strftime('%H:%M')
        
        # Vérifier si expirée
        is_expired = obj.end_time < timezone.now()
        is_future = obj.start_time > timezone.now()
        
        if is_expired:
            color = '#dc3545'  # Rouge
            status = '⏰ Expirée'
        elif is_future:
            color = '#ffc107'  # Jaune
            status = '🔮 Future'
        else:
            color = '#28a745'  # Vert
            status = '✅ Active'
        
        return format_html(
            '<div style="color: {};"><strong>{}</strong><br>'
            '<small>{} - {}</small></div>',
            color, status, start, end
        )
    datetime_info.short_description = 'Date/Heure'
    
    def status_badge(self, obj):
        """Afficher le statut avec couleur"""
        colors = {
            'pending': '#ffc107',
            'confirmed': '#17a2b8', 
            'rejected': '#dc3545',
            'cancelled': '#6c757d',
            'completed': '#28a745'
        }
        
        status_labels = {
            'pending': 'En attente',
            'confirmed': 'Confirmée',
            'rejected': 'Rejetée', 
            'cancelled': 'Annulée',
            'completed': 'Terminée'
        }
        
        color = colors.get(obj.status, '#6c757d')
        label = status_labels.get(obj.status, obj.status)
        
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, label
        )
    status_badge.short_description = 'Statut'
    
    def ticket_info(self, obj):
        """Afficher les infos ticket"""
        ticket = obj.ticket_set.first()
        if ticket:
            return format_html(
                '<strong>{}</strong><br>'
                '<small>Utilisé: {}</small>',
                ticket.ticket_number,
                '✅ Oui' if ticket.is_used else '❌ Non'
            )
        return '-'
    ticket_info.short_description = 'Ticket'
    
    def actions_column(self, obj):
        """Actions rapides"""
        actions = []
        
        # Bouton pour marquer comme terminée
        if obj.status == ReservationStatus.CONFIRMED:
            actions.append(
                f'<a class="button" href="{reverse("admin:reservations_reservation_change", args=[obj.pk])}">'
                '✏️ Modifier</a>'
            )
        
        # Bouton pour voir les détails
        actions.append(
            f'<a class="button" href="{reverse("admin:reservations_reservation_change", args=[obj.pk])}">'
            '👁️ Détails</a>'
        )
        
        return format_html(' '.join(actions))
    actions_column.short_description = 'Actions'
    
    # Dashboard personnalisé
    change_list_template = 'admin/reservations/reservation_change_list.html'
    
    def changelist_view(self, request, extra_context=None):
        """Ajouter le dashboard à la vue liste"""
        response = super().changelist_view(request, extra_context)
        
        # Statistiques
        total_reservations = Reservation.objects.count()
        confirmed_reservations = Reservation.objects.filter(status='confirmed').count()
        expired_reservations = Reservation.objects.filter(
            end_time__lt=timezone.now(),
            status='confirmed'
        ).count()
        completed_today = Reservation.objects.filter(
            status='completed',
            end_time__date=timezone.now().date()
        ).count()
        
        # Réservations expirées récentes
        recent_expired = Reservation.objects.filter(
            end_time__lt=timezone.now(),
            status='confirmed'
        ).order_by('-end_time')[:10]
        
        context = {
            'total_reservations': total_reservations,
            'confirmed_reservations': confirmed_reservations,
            'expired_reservations': expired_reservations,
            'completed_today': completed_today,
            'recent_expired': recent_expired,
        }
        
        response.context_data.update(context)
        return response
