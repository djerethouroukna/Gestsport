from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import json
from .models import Terrain, Equipment, Review, TerrainPhoto, TerrainStatus
from notifications.utils import NotificationService
from reservations.models import Reservation, ReservationStatus
import requests

# Coordinate parsing/validation helper
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def _parse_coordinate(val, is_lat=True):
    """Parse et valide une coordonnée en Decimal arrondie à 6 décimales.
    Raise ValueError en cas d'entrée invalide ou hors bornes.
    """
    if val in (None, ''):
        return None
    try:
        d = Decimal(str(val))
    except InvalidOperation:
        raise ValueError('Coordonnée invalide. Utilisez un nombre au format décimal.')
    # arrondir à 6 décimales
    d = d.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    # bornes géographiques
    if is_lat and (d < Decimal('-90') or d > Decimal('90')):
        raise ValueError('La latitude doit être comprise entre -90 et 90.')
    if not is_lat and (d < Decimal('-180') or d > Decimal('180')):
        raise ValueError('La longitude doit être comprise entre -180 et 180.')
    return d

@login_required
def terrain_list(request):
    """Liste des terrains avec filtres"""
    terrains = Terrain.objects.all().order_by('name')
    
    # Filtres
    terrain_type = request.GET.get('type')
    status_filter = request.GET.get('status')
    available_today = request.GET.get('available_today')
    prix_max = request.GET.get('prix_max')
    rating = request.GET.get('rating')
    
    if terrain_type:
        terrains = terrains.filter(terrain_type=terrain_type)
    if status_filter:
        terrains = terrains.filter(status=status_filter)
    if prix_max:
        terrains = terrains.filter(price_per_hour__lte=prix_max)
    if rating:
        terrains = terrains.filter(average_rating__gte=rating)
    
    # Filtre de disponibilité aujourd'hui
    if available_today == 'yes':
        # Vérifier les réservations aujourd'hui
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        # Terrains avec réservations aujourd'hui
        reserved_terrain_ids = Reservation.objects.filter(
            start_time__gte=today_start,
            start_time__lte=today_end,
            status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING]
        ).values_list('terrain_id', flat=True)
        
        # Afficher seulement les terrains NON réservés aujourd'hui
        terrains = terrains.exclude(id__in=reserved_terrain_ids)
        
    elif available_today == 'no':
        # Afficher seulement les terrains réservés aujourd'hui
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
        
        # Terrains avec réservations aujourd'hui
        reserved_terrain_ids = Reservation.objects.filter(
            start_time__gte=today_start,
            start_time__lte=today_end,
            status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING]
        ).values_list('terrain_id', flat=True)
        
        # Afficher seulement les terrains réservés aujourd'hui
        terrains = terrains.filter(id__in=reserved_terrain_ids)
    
    # Pagination
    paginator = Paginator(terrains, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Ajouter la disponibilité aujourd'hui pour chaque terrain
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    reserved_terrain_ids = Reservation.objects.filter(
        start_time__gte=today_start,
        start_time__lte=today_end,
        status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING]
    ).values_list('terrain_id', flat=True)
    
    # Ajouter la propriété is_available_today à chaque terrain
    for terrain in page_obj:
        terrain.is_available_today = terrain.id not in reserved_terrain_ids
    
    # Types pour filtre
    terrain_types = Terrain.terrain_type.field.choices
    
    # Statistiques pour le dashboard
    total_terrains = Terrain.objects.count()
    available_terrains = Terrain.objects.filter(status='available').count()
    
    # Calculer les réservations aujourd'hui (uniquement confirmées)
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Compter uniquement les réservations confirmées aujourd'hui
    today_reservations = Reservation.objects.filter(
        start_time__gte=today_start,
        start_time__lte=today_end,
        status=ReservationStatus.CONFIRMED
    ).count()
    
    # Debug: afficher les valeurs
    print(f"DEBUG: today={today}")
    print(f"DEBUG: today_start={today_start}")
    print(f"DEBUG: today_end={today_end}")
    print(f"DEBUG: today_reservations={today_reservations}")
    print(f"DEBUG: all confirmed reservations count={today_reservations}")
    
    # Calculer le prix moyen
    avg_price = Terrain.objects.aggregate(
        avg_price=Avg('price_per_hour')
    )['avg_price'] or 25
    
    # Comptes par type
    football_count = Terrain.objects.filter(terrain_type='football').count()
    tennis_count = Terrain.objects.filter(terrain_type='tennis').count()
    basketball_count = Terrain.objects.filter(terrain_type='basketball').count()
    volleyball_count = Terrain.objects.filter(terrain_type='volleyball').count()
    
    # Pourcentages simples
    if total_terrains > 0:
        football_percentage = (football_count / total_terrains) * 100
        tennis_percentage = (tennis_count / total_terrains) * 100
        basketball_percentage = (basketball_count / total_terrains) * 100
        volleyball_percentage = (volleyball_count / total_terrains) * 100
        available_percentage = (available_terrains / total_terrains) * 100
    else:
        football_percentage = tennis_percentage = basketball_percentage = volleyball_percentage = available_percentage = 0
    
    context = {
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'terrain_types': terrain_types,
        'selected_type': terrain_type,
        'selected_status': status_filter,
        'status_choices': TerrainStatus.choices,
        # Statistiques pour le dashboard
        'total_terrains': total_terrains,
        'available_count': available_terrains,
        'today_reservations': today_reservations,  # Valeur dynamique
        'avg_price': round(avg_price, 2) if avg_price else 25,  # Valeur dynamique
        # Pourcentages simples
        'football_count': football_count,
        'tennis_count': tennis_count,
        'basketball_count': basketball_count,
        'volleyball_count': volleyball_count,
        'football_percentage': football_percentage,
        'tennis_percentage': tennis_percentage,
        'basketball_percentage': basketball_percentage,
        'volleyball_percentage': volleyball_percentage,
        'available_percentage': available_percentage,
    }
    return render(request, 'terrains/terrain_list.html', context)

@login_required
def terrain_detail(request, terrain_id):
    """Détail d'un terrain avec réservation rapide"""
    terrain = get_object_or_404(Terrain, id=terrain_id)
    
    # Photos
    photos = terrain.photos.all().order_by('order')
    primary_photo = photos.filter(is_primary=True).first() or photos.first()
    
    # Équipements
    equipments = terrain.terrain_equipments.all()
    
    # Horaires
    opening_hours = terrain.opening_hours.all().order_by('day_of_week')
    
    # Avis approuvés
    approved_reviews = terrain.reviews.filter(is_approved=True).order_by('-created_at')[:5]
    
    # Vérifier si l'utilisateur a déjà donné un avis
    user_review = None
    if request.user.is_authenticated:
        user_review = terrain.reviews.filter(user=request.user).first()
    
    # Cartographie — si les champs latitude/longitude existent
    lat = getattr(terrain, 'latitude', None)
    lng = getattr(terrain, 'longitude', None)
    coords = None
    if lat is not None and lng is not None:
        coords = {'lat': float(lat), 'lng': float(lng)}

    context = {
        'terrain': terrain,
        'photos': photos,
        'primary_photo': primary_photo,
        'equipments': equipments,
        'opening_hours': opening_hours,
        'approved_reviews': approved_reviews,
        'user_review': user_review,
        'coords': coords
    }
    return render(request, 'terrains/terrain_detail.html', context)

@login_required
def quick_booking(request, terrain_id):
    """Réservation rapide depuis la page terrain"""
    terrain = get_object_or_404(Terrain, id=terrain_id)
    
    if request.method == 'POST':
        # Logique de réservation rapide
        date = request.POST.get('date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        # Appel à l'API de réservation
        try:
            reservation_data = {
                'terrain': terrain_id,
                'start_time': f"{date} {start_time}",
                'end_time': f"{date} {end_time}",
                'user': request.user.id
            }
            
            # Redirection vers la page de réservation avec données pré-remplies
            return JsonResponse({
                'success': True,
                'redirect_url': f"/reservations/create/?terrain={terrain_id}&date={date}&start_time={start_time}&end_time={end_time}"
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@require_GET
def terrain_availability(request, terrain_id):
    """Vérifier la disponibilité d'un terrain (AJAX)"""
    terrain = get_object_or_404(Terrain, id=terrain_id)

    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')

    if not start_time or not end_time:
        return JsonResponse({'available': False, 'error': 'start_time et end_time sont requis'})

    from datetime import datetime
    from django.utils import timezone

    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        if start_dt.tzinfo is None:
            start_dt = timezone.make_aware(start_dt)
        if end_dt.tzinfo is None:
            end_dt = timezone.make_aware(end_dt)
    except Exception:
        return JsonResponse({'available': False, 'error': 'Format de date invalide'})

    from terrains.utils import TerrainAvailabilityService
    availability = TerrainAvailabilityService.check_period_availability(terrain, start_dt, end_dt)

    return JsonResponse(availability)

@login_required
def terrain_create(request):
    """Créer un nouveau terrain (admin uniquement)"""
    if request.user.role != 'admin':
        return redirect('terrains:terrain_list')
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        name = request.POST.get('name')
        description = request.POST.get('description')
        terrain_type = request.POST.get('terrain_type')
        capacity = request.POST.get('capacity')
        price_per_hour = request.POST.get('price_per_hour')
        status = request.POST.get('status', 'available')
        
        # Créer le terrain directement
        try:
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')

            # Valider et parser les coordonnées
            try:
                lat_dec = _parse_coordinate(latitude, is_lat=True)
                lng_dec = _parse_coordinate(longitude, is_lat=False)
            except ValueError as ve:
                # Renvoyer une erreur de formulaire lisible
                return render(request, 'terrains/terrain_form.html', {
                    'error': str(ve),
                    'form_data': request.POST,
                    'terrain_types': Terrain.terrain_type.field.choices,
                    'status_choices': TerrainStatus.choices
                })

            terrain = Terrain.objects.create(
                name=name,
                description=description,
                terrain_type=terrain_type,
                capacity=int(capacity),
                price_per_hour=float(price_per_hour),
                status=status,
                latitude=lat_dec,
                longitude=lng_dec,
            )
            
            # Gérer l'upload des photos
            photos = request.FILES.getlist('photos')
            for i, photo in enumerate(photos[:5]):  # Limiter à 5 photos
                TerrainPhoto.objects.create(
                    terrain=terrain,
                    image=photo,
                    is_primary=(i == 0),  # Première photo comme principale
                    order=i
                )
            
            # Notifier les admins du nouveau terrain
            NotificationService.create_notification(
                recipient=request.user,
                title='Terrain créé',
                message=f'Le terrain "{terrain.name}" a été créé avec succès.',
                notification_type='system_message'
            )
            
            return redirect('terrains:terrain_list')
        except Exception as e:
            return render(request, 'terrains/terrain_form.html', {
                'error': str(e),
                'form_data': request.POST,
                'terrain_types': Terrain.terrain_type.field.choices,
                'status_choices': TerrainStatus.choices
            })
    
    # Afficher le formulaire
    return render(request, 'terrains/terrain_form.html', {
        'terrain_types': Terrain.terrain_type.field.choices,
        'status_choices': TerrainStatus.choices
    })

@login_required
def terrain_update(request, terrain_id):
    """Mettre à jour un terrain (admin uniquement)"""
    if request.user.role != 'admin':
        return redirect('terrains:terrain_detail', terrain_id=terrain_id)
    
    terrain = get_object_or_404(Terrain, id=terrain_id)
    
    if request.method == 'POST':
        # Mettre à jour directement
        try:
            terrain.name = request.POST.get('name')
            terrain.description = request.POST.get('description')
            terrain.terrain_type = request.POST.get('terrain_type')
            terrain.capacity = int(request.POST.get('capacity'))
            terrain.price_per_hour = float(request.POST.get('price_per_hour'))
            terrain.status = request.POST.get('status')

            # Coordonnées (si fournies)
            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')
            try:
                terrain.latitude = _parse_coordinate(lat, is_lat=True)
                terrain.longitude = _parse_coordinate(lng, is_lat=False)
            except ValueError as ve:
                return render(request, 'terrains/terrain_form.html', {
                    'terrain': terrain,
                    'error': str(ve),
                    'form_data': request.POST,
                    'terrain_types': Terrain.terrain_type.field.choices,
                    'status_choices': TerrainStatus.choices
                })

            terrain.save()
            
            # Gérer la suppression des photos cochées
            delete_photos = request.POST.getlist('delete_photos')
            for photo_id in delete_photos:
                TerrainPhoto.objects.filter(id=photo_id, terrain=terrain).delete()
            
            # Gérer l'upload des nouvelles photos
            photos = request.FILES.getlist('photos')
            current_order = terrain.photos.count()
            for i, photo in enumerate(photos[:5]):  # Limiter à 5 photos
                TerrainPhoto.objects.create(
                    terrain=terrain,
                    image=photo,
                    is_primary=(current_order == 0 and i == 0),  # Première photo comme principale si aucune autre
                    order=current_order + i
                )
            
            # Notifier de la mise à jour du terrain
            NotificationService.create_notification(
                recipient=request.user,
                title='Terrain mis à jour',
                message=f'Le terrain "{terrain.name}" a été mis à jour avec succès.',
                notification_type='system_message'
            )
            
            return redirect('terrains:terrain_detail', terrain_id=terrain_id)
        except Exception as e:
            return render(request, 'terrains/terrain_form.html', {
                'terrain': terrain,
                'error': str(e),
                'form_data': request.POST,
                'terrain_types': Terrain.terrain_type.field.choices,
                'status_choices': TerrainStatus.choices
            })
    
    # Afficher le formulaire avec les données actuelles
    return render(request, 'terrains/terrain_form.html', {
        'terrain': terrain,
        'terrain_types': Terrain.terrain_type.field.choices,
        'status_choices': TerrainStatus.choices,
        'photos': terrain.photos.all()
    })

@login_required
def terrain_delete(request, terrain_id):
    """Supprimer un terrain (admin uniquement)"""
    if request.user.role != 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Permission refusée'}, status=403)
        return redirect('terrains:terrain_detail', terrain_id=terrain_id)
    
    terrain = get_object_or_404(Terrain, id=terrain_id)
    
    if request.method == 'POST':
        # Supprimer directement
        try:
            terrain_name = terrain.name
            terrain.delete()
            
            # Notifier de la suppression du terrain
            try:
                NotificationService.create_notification(
                    recipient=request.user,
                    title='Terrain supprimé',
                    message=f'Le terrain "{terrain_name}" a été supprimé avec succès.',
                    notification_type='system_message'
                )
            except Exception as e:
                # Continue même si la notification échoue
                print(f"Erreur notification: {e}")
            
            # Retourner une réponse JSON pour les requêtes AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Terrain supprimé avec succès'})
            
            return redirect('terrains:terrain_list')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            return render(request, 'terrains/terrain_confirm_delete.html', {
                'terrain': terrain,
                'error': str(e)
            })
    
    # Afficher la page de confirmation
    return render(request, 'terrains/terrain_confirm_delete.html', {'terrain': terrain})

@login_required
def add_review(request, terrain_id):
    """Ajouter un avis sur un terrain"""
    terrain = get_object_or_404(Terrain, id=terrain_id)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Vérifier si l'utilisateur a déjà donné un avis
        existing_review = terrain.reviews.filter(user=request.user).first()
        if existing_review:
            # Mettre à jour l'avis existant
            existing_review.rating = rating
            existing_review.comment = comment
            existing_review.save()
        else:
            # Créer un nouvel avis
            Review.objects.create(
                terrain=terrain,
                user=request.user,
                rating=rating,
                comment=comment
            )
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@login_required
def terrain_availability(request, terrain_id):
    """Afficher la disponibilité d'un terrain avec calendrier interactif"""
    terrain = get_object_or_404(Terrain, id=terrain_id)
    
    # Récupérer les réservations pour les 30 prochains jours
    today = timezone.now().date()
    end_date = today + timedelta(days=30)
    
    reservations = Reservation.objects.filter(
        terrain=terrain,
        start_time__date__gte=today,
        start_time__date__lte=end_date,
        status__in=[ReservationStatus.CONFIRMED, ReservationStatus.PENDING]
    ).order_by('start_time')
    
    # Créer un dictionnaire de disponibilité
    availability = {}
    current_date = today
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        # Vérifier les réservations pour cette date
        day_reservations = [r for r in reservations if r.start_time.date() == current_date]
        
        # Déterminer les créneaux disponibles
        if not day_reservations:
            availability[date_str] = {
                'status': 'available',
                'slots': ['08:00-10:00', '10:00-12:00', '14:00-16:00', '16:00-18:00', '18:00-20:00'],
                'message': 'Disponible toute la journée'
            }
        else:
            # Calculer les créneaux occupés
            occupied_slots = []
            available_slots = ['08:00-10:00', '10:00-12:00', '14:00-16:00', '16:00-18:00', '18:00-20:00']
            
            for reservation in day_reservations:
                start_time = reservation.start_time.strftime('%H:%M')
                end_time = reservation.end_time.strftime('%H:%M')
                occupied_slots.append(f"{start_time}-{end_time}")
            
            # Retirer les créneaux occupés
            for slot in occupied_slots:
                if slot in available_slots:
                    available_slots.remove(slot)
            
            availability[date_str] = {
                'status': 'partial' if available_slots else 'full',
                'slots': available_slots,
                'occupied': occupied_slots,
                'message': f"{'Créneaux disponibles: ' + ', '.join(available_slots) if available_slots else 'Complet'}"
            }
        
        current_date += timedelta(days=1)
    
    # Si requête AJAX, retourner JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'terrain': {
                'id': terrain.id,
                'name': terrain.name,
                'capacity': terrain.capacity,
                'price_per_hour': str(terrain.price_per_hour)
            },
            'availability': availability,
            'reservations': [
                {
                    'date': r.start_time.strftime('%Y-%m-%d'),
                    'start_time': r.start_time.strftime('%H:%M'),
                    'end_time': r.end_time.strftime('%H:%M'),
                    'user': r.user.get_full_name() or r.user.email,
                    'status': r.status
                }
                for r in reservations
            ]
        })
    
    # Sinon, afficher le template
    context = {
        'terrain': terrain,
        'availability': json.dumps(availability),
        'reservations': reservations,
        'today': today.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }
    
    return render(request, 'terrains/terrain_availability.html', context)
