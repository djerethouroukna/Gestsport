from django.shortcuts import render, get_object_or_404, redirect

from django.contrib.auth.decorators import login_required

from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from django.urls import reverse_lazy

from django.contrib import messages

from django.db.models import Q

from django.http import JsonResponse

from decimal import Decimal



from .models import Activity, ActivityStatus

from .forms import ActivityForm

from terrains.models import Terrain

from reservations.models import Reservation, ReservationStatus

from reservations.forms import ReservationForm



class ActivityListView(LoginRequiredMixin, ListView):

    """Vue liste des activités"""

    model = Activity

    template_name = 'activities/activity_list.html'

    context_object_name = 'activities'

    paginate_by = 10



    def get_queryset(self):

        """Filtrer selon le rôle de l'utilisateur"""

        user = self.request.user

        

        if user.role == 'admin':

            return Activity.objects.all()

        elif user.role == 'coach':

            return Activity.objects.filter(coach=user)

        else:  # player

            return Activity.objects.filter(status=ActivityStatus.CONFIRMED)

    

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        
        # Obtenir toutes les activités selon le rôle
        activities = self.get_queryset()
        
        # Calculer les statistiques
        total_activities = activities.count()
        confirmed_activities = activities.filter(status=ActivityStatus.CONFIRMED).count()
        pending_activities = activities.filter(status=ActivityStatus.PENDING).count()
        
        # Activités d'aujourd'hui (créées aujourd'hui)
        from django.utils import timezone
        today = timezone.now().date()
        today_activities = activities.filter(created_at__date=today).count()
        
        # Calculer les pourcentages
        confirmed_percentage = (confirmed_activities / total_activities * 100) if total_activities > 0 else 0
        pending_percentage = (pending_activities / total_activities * 100) if total_activities > 0 else 0
        today_percentage = (today_activities / total_activities * 100) if total_activities > 0 else 0
        
        # Ajouter au contexte
        context.update({
            'total_activities': total_activities,
            'confirmed_activities': confirmed_activities,
            'pending_activities': pending_activities,
            'today_activities': today_activities,
            'confirmed_percentage': confirmed_percentage,
            'pending_percentage': pending_percentage,
            'today_percentage': today_percentage,
            'terrains': Terrain.objects.all()
        })

        return context



class ActivityDetailView(LoginRequiredMixin, DetailView):

    """Vue détail d'une activité"""

    model = Activity

    template_name = 'activities/activity_detail.html'

    context_object_name = 'activity'

    

    def get_queryset(self):

        """Filtrer selon le rôle de l'utilisateur"""

        user = self.request.user

        

        if user.role == 'admin':

            return Activity.objects.all()

        elif user.role == 'coach':

            return Activity.objects.filter(coach=user)

        else:  # player

            return Activity.objects.filter(status=ActivityStatus.CONFIRMED)

    

    def dispatch(self, request, *args, **kwargs):

        """Vérifier les permissions avant d'accéder au détail"""

        activity = self.get_object()

        

        # Admin peut voir tout

        if request.user.role == 'admin':

            return super().dispatch(request, *args, **kwargs)

        

        # Coach ne peut voir que ses activités

        if request.user.role == 'coach' and activity.coach != request.user:

            messages.error(request, "Vous n'avez pas la permission de voir cette activité.")

            return redirect('activities:activity_list')

        

        # Player ne peut voir que les activités confirmées

        if request.user.role == 'player' and activity.status != ActivityStatus.CONFIRMED:

            messages.error(request, "Cette activité n'est pas encore disponible.")

            return redirect('activities:activity_list')

        

        return super().dispatch(request, *args, **kwargs)



class ActivityCreateView(LoginRequiredMixin, CreateView):

    """Vue création d'activité"""

    model = Activity

    form_class = ActivityForm

    template_name = 'activities/activity_create.html'

    success_url = reverse_lazy('activities:activity_list')



    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['terrains'] = Terrain.objects.all()

        return context



    def form_valid(self, form):

        form.instance.coach = self.request.user

        

        # La validation des conflits est déjà faite dans le formulaire (méthode clean)

        # Si on arrive ici, c'est que le formulaire est valide

        

        # Statut par défaut selon le rôle de l'utilisateur

        if self.request.user.role == 'admin':

            form.instance.status = ActivityStatus.CONFIRMED

            messages.success(self.request, 'Activité créée et confirmée.')

        else:

            form.instance.status = ActivityStatus.PENDING

            messages.info(self.request, 'Activité créée. Elle est en attente de confirmation par un administrateur.')



        return super().form_valid(form)



class ActivityUpdateView(LoginRequiredMixin, UpdateView):

    """Vue modification d'activité"""

    model = Activity

    form_class = ActivityForm

    template_name = 'activities/activity_update.html'

    success_url = reverse_lazy('activities:activity_list')



    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context['terrains'] = Terrain.objects.all()

        return context



    def dispatch(self, request, *args, **kwargs):

        """Vérifier les permissions"""

        activity = self.get_object()

        

        # Seul le coach propriétaire peut modifier son activité

        if activity.coach != request.user:

            messages.error(request, "Seul le coach propriétaire peut modifier cette activité.")

            return redirect('activities:activity_detail', pk=activity.pk)

        

        # Une activité confirmée ne peut plus être modifiée

        if activity.status == ActivityStatus.CONFIRMED:

            messages.error(request, "Cette activité est déjà confirmée et ne peut plus être modifiée.")

            return redirect('activities:activity_detail', pk=activity.pk)

        

        return super().dispatch(request, *args, **kwargs)



    def form_valid(self, form):

        messages.success(self.request, 'Activité modifiée avec succès!')

        return super().form_valid(form)



class ActivityDeleteView(LoginRequiredMixin, DeleteView):

    """Vue suppression d'activité"""

    model = Activity

    template_name = 'activities/activity_confirm_delete.html'

    success_url = reverse_lazy('activities:activity_list')



    def dispatch(self, request, *args, **kwargs):

        """Vérifier les permissions"""

        activity = self.get_object()

        if request.user.role != 'admin' and activity.coach != request.user:

            messages.error(request, "Vous n'avez pas la permission de supprimer cette activité.")

            return redirect('activities:activity_detail', pk=activity.pk)

        return super().dispatch(request, *args, **kwargs)



    def delete(self, request, *args, **kwargs):

        messages.success(request, 'Activité supprimée avec succès!')

        return super().delete(request, *args, **kwargs)



# Vues fonctionnelles pour compatibilité HOUROUGBELLE-05

@login_required

def activity_list(request):

    """Vue liste des activités (version fonctionnelle)"""

    # Utiliser la vue class-based directement avec les bons paramètres

    view = ActivityListView.as_view()

    return view(request)



@login_required

def activity_detail(request, pk):

    """Vue détail d'activité (version fonctionnelle)"""

    view = ActivityDetailView.as_view()

    return view(request, pk=pk)



@login_required

def activity_create(request):

    """Vue création d'activité (version fonctionnelle)"""

    view = ActivityCreateView.as_view()

    return view(request)



@login_required

def activity_update(request, pk):

    """Vue modification d'activité (version fonctionnelle)"""

    view = ActivityUpdateView.as_view()

    return view(request, pk=pk)



@login_required

def activity_delete(request, pk):

    """Vue suppression d'activité (version fonctionnelle)"""

    view = ActivityDeleteView.as_view()

    return view(request, pk=pk)





@login_required

def activity_join(request, pk):

    """Permettre à l'utilisateur courant de rejoindre une activité"""

    activity = get_object_or_404(Activity, pk=pk)

    if request.user not in activity.participants.all():

        activity.participants.add(request.user)

        messages.success(request, 'Vous avez rejoint l\'activité.')

    else:

        messages.info(request, 'Vous participez déjà à cette activité.')

    return redirect('activities:activity_detail', pk=pk)



@login_required

def unified_planning(request):

    """Vue unifiée des activités et réservations"""

    from reservations.models import Reservation

    from terrains.models import Terrain

    

    # Récupérer toutes les activités et réservations

    activities = Activity.objects.all()

    reservations = Reservation.objects.all()

    terrains = Terrain.objects.all()

    

    # Combiner et trier par date

    unified_bookings = []

    

    # Ajouter les activités

    for activity in activities:

        unified_bookings.append({

            'type': 'activity',

            'id': activity.id,

            'date': activity.start_time,

            'start_time': activity.start_time,

            'end_time': activity.end_time,

            'terrain': activity.terrain,

            'title': activity.title,

            'description': activity.description,

            'organizer': activity.coach,

            'status': activity.status,

            'activity_type': activity.activity_type,

        })

    

    # Ajouter les réservations

    for reservation in reservations:

        unified_bookings.append({

            'type': 'reservation',

            'id': reservation.id,

            'date': reservation.start_time,

            'start_time': reservation.start_time,

            'end_time': reservation.end_time,

            'terrain': reservation.terrain,

            'title': 'Réservation',

            'description': reservation.notes,

            'organizer': reservation.user,

            'status': reservation.status,

            'notes': reservation.notes,

        })

    

    # Trier par date de début

    unified_bookings.sort(key=lambda x: x['start_time'], reverse=True)

    

    # Calculer les statistiques

    total_bookings = len(unified_bookings)

    conflicts = []  # TODO: Implémenter la détection de conflits

    

    context = {

        'unified_bookings': unified_bookings,

        'activities': activities,

        'reservations': reservations,

        'terrains': terrains,

        'total_bookings': total_bookings,

        'conflicts': conflicts,

    }

    

    return render(request, 'activities/unified_planning.html', context)





@login_required

def activity_confirm(request, pk):

    """Confirmer une activité (admin seulement) et bloquer les créneaux correspondants"""

    if request.method != 'POST':

        return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

    

    activity = get_object_or_404(Activity, pk=pk)



    # Vérifier les permissions

    if request.user.role != 'admin':

        return JsonResponse({'success': False, 'message': "Vous n'avez pas la permission de confirmer cette activité."}, status=403)



    # Vérifier que l'activité est en attente

    from activities.models import ActivityStatus

    if activity.status != ActivityStatus.PENDING:

        return JsonResponse({'success': False, 'message': 'Cette activité n\'est pas en attente.'}, status=400)



    # Vérifier de nouveau la disponibilité

    from reservations.models import Reservation, ReservationStatus

    from timeslots.services import TimeSlotService as TSService



    terrain = activity.terrain

    start_time = activity.start_time

    end_time = activity.end_time



    reservation_conflict = Reservation.objects.filter(

        terrain=terrain,

        status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED],

        start_time__lt=end_time,

        end_time__gt=start_time

    ).exists()



    # Ne pas considérer la même activité dans le filtre (on cherche d'autres activités confirmées)

    activity_conflict = Activity.objects.filter(

        terrain=terrain,

        status=ActivityStatus.CONFIRMED,

        start_time__lt=end_time,

        end_time__gt=start_time

    ).exclude(pk=activity.pk).exists()



    is_available_ts, ts_conflicts = TSService.check_availability(terrain, start_time, end_time)



    if reservation_conflict or activity_conflict or not is_available_ts:

        msg = 'Le terrain n\'est pas disponible pour cet intervalle. La confirmation a échoué.'

        if reservation_conflict:

            msg += ' Conflit avec une réservation existante.'

        if activity_conflict:

            msg += ' Conflit avec une activité confirmée existante.'

        if not is_available_ts:

            msg += f' {len(ts_conflicts)} créneaux bloqués.'

        return JsonResponse({'success': False, 'message': msg}, status=400)



    # Bloquer les créneaux et confirmer l'activité

    try:

        TSService.block_timeslots(terrain, start_time, end_time, reason=f"Activité: {activity.title}", created_by=request.user)

        activity.status = ActivityStatus.CONFIRMED

        activity.save()



        # Notification au coach

        try:

            from notifications.utils import NotificationService

            NotificationService.create_notification(

                recipient=activity.coach,

                title="Activité validée",

                message=f"Votre activité '{activity.title}' a été validée.",

                notification_type='activity_reminder',

                content_object=activity

            )

        except Exception:

            pass  # Ne pas échouer la confirmation si la notification échoue



        return JsonResponse({'success': True, 'message': 'Activité confirmée avec succès!'})

    except Exception as e:

        return JsonResponse({'success': False, 'message': f'La confirmation a échoué: {str(e)}'}, status=500)



@login_required

def activity_leave(request, pk):

    """Permettre à l'utilisateur courant de quitter une activité"""

    activity = get_object_or_404(Activity, pk=pk)

    if request.user in activity.participants.all():

        activity.participants.remove(request.user)

        messages.success(request, 'Vous avez quitté l\'activité.')

    else:

        messages.info(request, 'Vous ne participez pas à cette activité.')

    return redirect('activities:activity_detail', pk=pk)





@login_required

def activity_reservation_create(request, activity_id):

    """

    Vue de création de réservation liée à une activité confirmée

    """

    print(f"=== ACTIVITY RESERVATION CREATE pour activité {activity_id} ===")

    print(f"Template utilisé: activities/reservation_form.html")

    

    # Récupérer l'activité

    activity = get_object_or_404(Activity, id=activity_id)

    

    # Vérifier que l'activité est confirmée

    if activity.status != ActivityStatus.CONFIRMED:

        messages.error(request, 'Cette activité n\'est pas encore confirmée. Impossible de faire une réservation.')

        return redirect('activities:activity_detail', pk=activity_id)

    

    # Vérifier que l'utilisateur a le droit de réserver

    if activity.coach != request.user and request.user.role != 'admin':

        messages.error(request, 'Vous n\'êtes pas autorisé à réserver pour cette activité.')

        return redirect('activities:activity_detail', pk=activity_id)

    

    # Vérifier si une réservation existe déjà

    if hasattr(activity, 'reservation') and activity.reservation:

        messages.info(request, 'Une réservation existe déjà pour cette activité.')

        return redirect('reservations:reservation_detail', pk=activity.reservation.id)

    

    if request.method == 'POST':

        print("POST reçu pour création réservation")

        form = ReservationForm(request.POST)

        pay_now = request.POST.get('pay_now') == 'true'

        

        if form.is_valid():

            print("Formulaire valide")

            

            # Créer la réservation liée à l'activité

            reservation = form.save(commit=False)

            reservation.user = request.user

            reservation.activity = activity

            

            # Si paiement immédiat, confirmer directement

            if pay_now:

                reservation.status = ReservationStatus.CONFIRMED

            else:

                reservation.status = ReservationStatus.PENDING

            

            # FORCER les heures de l'activité (écraser toute modification)

            reservation.start_time = activity.start_time

            reservation.end_time = activity.end_time

            

            reservation.save()

            

            # Calculer le montant total

            from reservations.utils import calculate_reservation_amount

            reservation.total_amount = calculate_reservation_amount(reservation)

            reservation.save()

            

            print(f"Réservation créée: {reservation.id} pour activité {activity.title}")

            

            # Si requête AJAX pour paiement immédiat

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                if pay_now:

                    # Créer le paiement et générer QR code

                    try:

                        from payments.stripe_service import StripeService

                        from payments.models import Payment

                        import qrcode

                        import io

                        import base64

                        

                        # Créer le paiement

                        payment = Payment.objects.create(

                            reservation=reservation,

                            user=request.user,

                            amount=reservation.total_amount,

                            currency='XOF',

                            status='paid',  # Marquer comme payé pour QR code

                            payment_method=None

                        )

                        

                        # Générer le QR code

                        qr_data = f"RESERVATION:{reservation.id}:USER:{request.user.id}:PAID:{payment.id}"

                        qr = qrcode.QRCode(version=1, box_size=10, border=5)

                        qr.add_data(qr_data)

                        qr.make(fit=True)

                        

                        img = qr.make_image(fill_color="black", back_color="white")

                        buffer = io.BytesIO()

                        img.save(buffer, format='PNG')

                        qr_image = base64.b64encode(buffer.getvalue()).decode()

                        

                        return JsonResponse({

                            'success': True,

                            'qr_code': f'data:image/png;base64,{qr_image}',

                            'reservation_id': reservation.id

                        })

                        

                    except Exception as e:

                        print(f"Erreur paiement QR: {e}")

                        return JsonResponse({

                            'success': False,

                            'message': str(e)

                        })

                else:

                    return JsonResponse({

                        'success': True,

                        'message': 'Réservation créée avec succès'

                    })

            

            # Traitement normal (non-AJAX)

            if pay_now:

                messages.success(request, f'Votre réservation pour l\'activité "{activity.title}" a été créée et payée avec succès! QR Code généré.')

            else:

                messages.success(request, f'Votre réservation pour l\'activité "{activity.title}" a été créée avec succès! Elle est en attente de confirmation par l\'administrateur.')

            

            # Envoyer notification à l'admin (si activé)

            try:

                from notifications.signals import reservation_status_change_notification

                reservation_status_change_notification(sender=Reservation, instance=reservation, created=True)

                print("Notification envoyée à l'admin")

            except Exception as e:

                print(f"Erreur notification: {e}")

            

            return redirect('reservations:reservation_detail', pk=reservation.id)

        else:

            print("Formulaire invalide:", form.errors)

            

            # Si requête AJAX, retourner les erreurs

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                return JsonResponse({

                    'success': False,

                    'message': 'Formulaire invalide',

                    'errors': form.errors

                })

            

            messages.error(request, 'Le formulaire contient des erreurs. Veuillez corriger.')

    else:

        # Pré-remplir le formulaire avec les données de l'activité

        form = ReservationForm(initial={

            'terrain': activity.terrain,

            'start_time': activity.start_time,

            'end_time': activity.end_time,

            'notes': f'Réservation pour l\'activité: {activity.title}'

        })

    

    context = {

        'activity': activity,

        'form': form,

        'terrains': Terrain.objects.all(),

    }

    

    return render(request, 'activities/reservation_form.html', context)

