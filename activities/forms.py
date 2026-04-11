from django import forms
from .models import Activity, ActivityType, ActivityStatus
from terrains.models import Terrain

class ActivityForm(forms.ModelForm):
    """Formulaire pour créer et modifier une activité"""
    
    class Meta:
        model = Activity
        fields = [
            'title', 'description', 'activity_type', 
            'terrain', 'max_participants', 'start_time', 'end_time'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de l\'activité'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description détaillée de l\'activité'
            }),
            'activity_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'terrain': forms.Select(attrs={
                'class': 'form-select'
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        
        # Personnaliser les labels
        self.fields['title'].label = 'Titre de l\'activité'
        self.fields['description'].label = 'Description'
        self.fields['activity_type'].label = 'Type d\'activité'
        self.fields['terrain'].label = 'Terrain'
        self.fields['max_participants'].label = 'Nombre maximum de participants'
        self.fields['start_time'].label = 'Date et heure de début'
        self.fields['end_time'].label = 'Date et heure de fin'
    
    def clean(self):
        """Validation personnalisée"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        terrain = cleaned_data.get('terrain')
        max_participants = cleaned_data.get('max_participants')
        
        # Vérifier que la date de fin est après la date de début
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError(
                'La date de fin doit être postérieure à la date de début.'
            )
        
        # Vérifier le nombre de participants
        if max_participants and (max_participants < 1 or max_participants > 50):
            raise forms.ValidationError(
                'Le nombre de participants doit être entre 1 et 50.'
            )
        
        # Validation de disponibilité du terrain
        if start_time and end_time and terrain:
            # Vérifier les conflits avec réservations existantes
            from reservations.models import Reservation, ReservationStatus
            conflicting = Reservation.objects.filter(
                terrain=terrain,
                status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exists()

            # Vérifier les conflits avec autres activités
            from activities.models import Activity, ActivityStatus
            activity_conflict = Activity.objects.filter(
                terrain=terrain,
                status=ActivityStatus.CONFIRMED,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).exclude(id=self.instance.id if self.instance else None).exists()

            # Vérifier la disponibilité via TimeSlotService
            from timeslots.services import TimeSlotService
            is_available_ts, ts_conflicts = TimeSlotService.check_availability(
                terrain, start_time, end_time
            )

            if conflicting:
                raise forms.ValidationError(
                    f"Ce terrain n'est pas disponible pour la période sélectionnée. "
                    f"Une réservation existe déjà pour ce créneau. "
                    f"Veuillez choisir un autre créneau."
                )
            
            if activity_conflict:
                raise forms.ValidationError(
                    f"Ce terrain n'est pas disponible pour la période sélectionnée. "
                    f"Une autre activité est déjà programmée. "
                    f"Veuillez choisir un autre créneau."
                )
            
            if not is_available_ts:
                raise forms.ValidationError(
                    f"Ce terrain n'est pas disponible pour la période sélectionnée. "
                    f"Les créneaux horaires sont déjà bloqués. "
                    f"Veuillez choisir un autre créneau."
                )
        
        return cleaned_data
    
    def clean_max_participants(self):
        """Validation du nombre maximum de participants"""
        max_participants = self.cleaned_data.get('max_participants')
        if max_participants and max_participants < 1:
            raise forms.ValidationError('Le nombre minimum de participants est 1.')
        if max_participants and max_participants > 50:
            raise forms.ValidationError('Le nombre maximum de participants est 50.')
        return max_participants
