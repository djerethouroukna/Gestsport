# timeslots/admin.py
from django.contrib import admin
from .models import TimeSlot, AvailabilityRule, TimeSlotGeneration, TimeSlotBlock


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'date', 'start_time', 'end_time', 'status', 'reservation', 'effective_price')
    list_filter = ('terrain', 'status', 'date', 'is_recurring')
    search_fields = ('terrain__name', 'reservation__user__email', 'reservation__user__first_name')
    ordering = ('-date', 'start_time')
    readonly_fields = ('id', 'duration_minutes', 'duration_hours', 'is_available', 'can_be_booked', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('terrain', 'date', 'start_time', 'end_time', 'status')
        }),
        ('Réservation', {
            'fields': ('reservation',)
        }),
        ('Prix', {
            'fields': ('price_override', 'effective_price')
        }),
        ('Récurrence', {
            'fields': ('is_recurring', 'recurring_pattern')
        }),
        ('Propriétés calculées', {
            'fields': ('duration_minutes', 'duration_hours', 'is_available', 'can_be_booked'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def effective_price(self, obj):
        from .services import TimeSlotService
        return TimeSlotService.get_timeslot_price(obj)
    effective_price.short_description = 'Prix effectif'


@admin.register(AvailabilityRule)
class AvailabilityRuleAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'name', 'rule_type', 'priority', 'is_active', 'start_date', 'end_date')
    list_filter = ('terrain', 'rule_type', 'is_active', 'priority')
    search_fields = ('terrain__name', 'name', 'description')
    ordering = ('-priority', 'created_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('terrain', 'rule_type', 'name', 'description', 'priority', 'is_active')
        }),
        ('Période', {
            'fields': ('start_date', 'end_date')
        }),
        ('Heures', {
            'fields': ('start_time', 'end_time')
        }),
        ('Jours de la semaine', {
            'fields': ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
        }),
        ('Prix', {
            'fields': ('price_multiplier', 'price_override')
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(TimeSlotGeneration)
class TimeSlotGenerationAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'start_date', 'end_date', 'slot_duration', 'slots_generated', 'generation_method', 'created_by', 'created_at')
    list_filter = ('terrain', 'generation_method', 'slot_duration', 'created_at')
    search_fields = ('terrain__name', 'created_by__email')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'slots_generated', 'created_at')


@admin.register(TimeSlotBlock)
class TimeSlotBlockAdmin(admin.ModelAdmin):
    list_display = ('terrain', 'start_datetime', 'end_datetime', 'reason', 'is_maintenance', 'created_by', 'created_at')
    list_filter = ('terrain', 'is_maintenance', 'created_at')
    search_fields = ('terrain__name', 'reason', 'created_by__email')
    ordering = ['-created_at']
    readonly_fields = ('id', 'created_at')
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('terrain', 'start_datetime', 'end_datetime', 'reason', 'is_maintenance')
        }),
        ('Création', {
            'fields': ('created_by',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        })
    )
