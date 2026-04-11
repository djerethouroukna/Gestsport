# activities/admin.py
from django.contrib import admin
from .models import Activity

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'activity_type', 'terrain', 'coach', 'start_time', 'status')
    list_filter = ('activity_type', 'status', 'start_time')
    search_fields = ('title', 'description', 'terrain__name', 'coach__email')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('terrain', 'coach', 'participants')
    date_hierarchy = 'start_time'
    actions = ['confirm_activities']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'description', 'activity_type', 'status')
        }),
        ('Planification', {
            'fields': ('terrain', 'coach', 'start_time', 'end_time')
        }),
        ('Participants', {
            'fields': ('participants', 'max_participants')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def confirm_activities(self, request, queryset):
        """Action d'administration pour confirmer plusieurs activités et bloquer les créneaux."""
        from timeslots.services import TimeSlotService as TSService
        from activities.models import ActivityStatus
        success = 0
        failed = 0

        for activity in queryset:
            if activity.status != ActivityStatus.PENDING:
                continue

            terrain = activity.terrain
            start_time = activity.start_time
            end_time = activity.end_time

            # Vérifier les conflits
            from reservations.models import Reservation, ReservationStatus
            reservation_conflict = Reservation.objects.filter(
                terrain=terrain,
                status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exists()

            activity_conflict = Activity.objects.filter(
                terrain=terrain,
                status=ActivityStatus.CONFIRMED,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exclude(pk=activity.pk).exists()

            is_available_ts, ts_conflicts = TSService.check_availability(terrain, start_time, end_time)

            if reservation_conflict or activity_conflict or not is_available_ts:
                failed += 1
                continue

            try:
                TSService.block_timeslots(terrain, start_time, end_time, reason=f"Activité: {activity.title}", created_by=request.user)
                activity.status = ActivityStatus.CONFIRMED
                activity.save()

                # Notification au coach
                from notifications.utils import NotificationService
                NotificationService.create_notification(
                    recipient=activity.coach,
                    title="Activité validée",
                    message=f"Votre activité '{activity.title}' a été validée par l'administrateur.",
                    notification_type='activity_reminder',
                    content_object=activity
                )

                success += 1
            except Exception:
                failed += 1

        self.message_user(request, f"{success} activités confirmées, {failed} échecs.")
    confirm_activities.short_description = 'Confirmer les activités sélectionnées (bloquer les créneaux)'
