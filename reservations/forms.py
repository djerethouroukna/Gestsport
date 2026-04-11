from django import forms
from django.utils import timezone
from .models import Reservation
from terrains.models import Terrain

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['terrain', 'start_time', 'end_time', 'notes']
        widgets = {
            'terrain': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes optionnelles...'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['terrain'].queryset = Terrain.objects.all()
        
        # Définir les valeurs minimales pour les champs datetime
        now = timezone.now()
        self.fields['start_time'].widget.attrs['min'] = now.strftime('%Y-%m-%dT%H:%M')
        self.fields['end_time'].widget.attrs['min'] = now.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        print("=== DEBUG form clean ===")
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        terrain = cleaned_data.get('terrain')

        print(f"Form data: terrain={terrain}, start={start_time}, end={end_time}")

        # Validation des dates de base
        if start_time and end_time:
            if start_time >= end_time:
                print("Erreur: start >= end")
                raise forms.ValidationError("L'heure de fin doit être postérieure à l'heure de début")
            
            if start_time <= timezone.now():
                print("Erreur: start in past")
                raise forms.ValidationError("La réservation ne peut pas être dans le passé")
            
            # Vérifier que la durée n'est pas trop longue (max 4 heures)
            duration = end_time - start_time
            if duration.total_seconds() > 4 * 3600:
                print("Erreur: duration too long")
                raise forms.ValidationError("La réservation ne peut pas dépasser 4 heures")

        # La validation de disponibilité est gérée dans la vue
        # pour éviter les conflits avec l'activité existante
        
        print("Form clean successful")
        return cleaned_data
