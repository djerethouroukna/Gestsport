from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json

from reservations.models import Reservation, ReservationStatus
from terrains.models import Terrain
from django.contrib.auth import get_user_model

User = get_user_model()

@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def simple_reservation_api(request):
    """API simple pour les réservations (contourne DRF)"""
    
    if request.method == 'GET':
        # Lister toutes les réservations
        reservations = Reservation.objects.select_related('terrain', 'user').all()
        
        reservations_data = []
        for reservation in reservations:
            reservations_data.append({
                'id': reservation.id,
                'user_name': reservation.user.get_full_name() or reservation.user.email,
                'terrain_name': reservation.terrain.name,
                'terrain': reservation.terrain.id,
                'start_time': reservation.start_time.isoformat(),
                'end_time': reservation.end_time.isoformat(),
                'status': reservation.status,
                'status_display': reservation.get_status_display(),
                'notes': reservation.notes,
                'created_at': reservation.created_at.isoformat(),
                'updated_at': reservation.updated_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'reservations': reservations_data
        })
    
    elif request.method == 'POST':
        # Créer une nouvelle réservation
        try:
            data = json.loads(request.body)
            
            # Validation de base
            if not all(key in data for key in ['terrain', 'start_time', 'end_time']):
                return JsonResponse({
                    'success': False,
                    'error': 'Champs requis: terrain, start_time, end_time'
                }, status=400)
            
            # Récupérer le terrain
            try:
                terrain = Terrain.objects.get(id=data['terrain'])
            except Terrain.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Terrain non trouvé'
                }, status=404)
            
            # Créer la réservation (utilisateur par défaut pour l'instant)
            user = User.objects.filter(role='admin').first()
            
            if not user:
                return JsonResponse({
                    'success': False,
                    'error': 'Utilisateur admin non trouvé'
                }, status=500)
            
            # Validation et conversion des dates
            from datetime import datetime
            try:
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Format de date invalide: {str(e)}'
                }, status=400)
            
            # Validation logique
            if start_time >= end_time:
                return JsonResponse({
                    'success': False,
                    'error': 'La date de fin doit être après la date de début'
                }, status=400)
            
            if start_time < timezone.now():
                return JsonResponse({
                    'success': False,
                    'error': 'La date de début ne peut pas être dans le passé'
                }, status=400)
            
            reservation = Reservation.objects.create(
                user=user,
                terrain=terrain,
                start_time=start_time,
                end_time=end_time,
                notes=data.get('notes', ''),
                status=ReservationStatus.PENDING
            )
            
            return JsonResponse({
                'success': True,
                'reservation': {
                    'id': reservation.id,
                    'user_name': reservation.user.get_full_name() or reservation.user.email,
                    'terrain_name': reservation.terrain.name,
                    'terrain': reservation.terrain.id,
                    'start_time': reservation.start_time.isoformat(),
                    'end_time': reservation.end_time.isoformat(),
                    'status': reservation.status,
                    'status_display': reservation.get_status_display(),
                    'notes': reservation.notes,
                    'created_at': reservation.created_at.isoformat()
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'JSON invalide'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def simple_reservation_detail_api(request, reservation_id):
    """API simple pour les détails d'une réservation"""
    
    try:
        reservation = Reservation.objects.select_related('terrain', 'user').get(id=reservation_id)
    except Reservation.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Réservation non trouvée'
        }, status=404)
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'reservation': {
                'id': reservation.id,
                'user_name': reservation.user.get_full_name() or reservation.user.email,
                'terrain_name': reservation.terrain.name,
                'terrain': reservation.terrain.id,
                'start_time': reservation.start_time.isoformat(),
                'end_time': reservation.end_time.isoformat(),
                'status': reservation.status,
                'status_display': reservation.get_status_display(),
                'notes': reservation.notes,
                'created_at': reservation.created_at.isoformat()
            }
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Mettre à jour les champs
            if 'terrain' in data:
                reservation.terrain = Terrain.objects.get(id=data['terrain'])
            if 'start_time' in data:
                reservation.start_time = data['start_time']
            if 'end_time' in data:
                reservation.end_time = data['end_time']
            if 'notes' in data:
                reservation.notes = data['notes']
            if 'status' in data:
                reservation.status = data['status']
            
            reservation.save()
            
            return JsonResponse({
                'success': True,
                'reservation': {
                    'id': reservation.id,
                    'user_name': reservation.user.get_full_name() or reservation.user.email,
                    'terrain_name': reservation.terrain.name,
                    'terrain': reservation.terrain.id,
                    'start_time': reservation.start_time.isoformat(),
                    'end_time': reservation.end_time.isoformat(),
                    'status': reservation.status,
                    'status_display': reservation.get_status_display(),
                    'notes': reservation.notes,
                    'created_at': reservation.created_at.isoformat()
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    elif request.method == 'PUT':
        # Modifier une réservation existante
        try:
            data = json.loads(request.body)
            reservation_id = data.get('id')
            
            if not reservation_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID de réservation requis'
                }, status=400)
            
            try:
                reservation = Reservation.objects.get(id=reservation_id)
            except Reservation.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Réservation non trouvée'
                }, status=404)
            
            # Mettre à jour les champs
            if 'terrain' in data:
                terrain = Terrain.objects.get(id=data['terrain'])
                reservation.terrain = terrain
            if 'start_time' in data:
                reservation.start_time = data['start_time']
            if 'end_time' in data:
                reservation.end_time = data['end_time']
            if 'status' in data:
                reservation.status = data['status']
            if 'notes' in data:
                reservation.notes = data['notes']
            
            reservation.save()
            
            return JsonResponse({
                'success': True,
                'reservation': {
                    'id': reservation.id,
                    'user_name': reservation.user.get_full_name() or reservation.user.email,
                    'terrain_name': reservation.terrain.name,
                    'terrain': reservation.terrain.id,
                    'start_time': reservation.start_time.isoformat(),
                    'end_time': reservation.end_time.isoformat(),
                    'status': reservation.status,
                    'status_display': reservation.get_status_display(),
                    'notes': reservation.notes,
                    'created_at': reservation.created_at.isoformat()
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    elif request.method == 'DELETE':
        # Supprimer une réservation
        try:
            data = json.loads(request.body)
            reservation_id = data.get('id')
            
            if not reservation_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID de réservation requis'
                }, status=400)
            
            try:
                reservation = Reservation.objects.get(id=reservation_id)
                reservation_name = f"#{reservation.id} - {reservation.terrain.name}"
                reservation.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Réservation "{reservation_name}" supprimée avec succès'
                })
                
            except Reservation.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Réservation non trouvée'
                }, status=404)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
