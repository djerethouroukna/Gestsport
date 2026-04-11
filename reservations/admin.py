# reservations/admin.py
from django.contrib import admin
from .models import Reservation

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'user', 'start_time', 'end_time', 'status')
    list_filter = ('status', 'start_time')
    search_fields = ('user__email', 'terrain__name', 'notes')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('user', 'terrain')
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Détails de la réservation', {
            'fields': ('user', 'terrain', 'status')
        }),
        ('Période', {
            'fields': ('start_time', 'end_time')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )