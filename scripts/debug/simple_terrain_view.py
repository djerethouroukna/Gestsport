#!/usr/bin/env python
import os
import django
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from terrains.models import Terrain

@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def simple_terrain_api(request):
    """API simple pour créer, lister, modifier et supprimer les terrains"""
    
    if request.method == 'GET':
        # Lister tous les terrains
        try:
            terrains = Terrain.objects.all().values(
                'id', 'name', 'description', 'terrain_type', 
                'capacity', 'price_per_hour', 'status', 'average_rating', 'image'
            )
            return JsonResponse({
                'success': True,
                'count': len(terrains),
                'results': list(terrains)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    elif request.method == 'POST':
        # Créer un nouveau terrain
        try:
            data = json.loads(request.body)
            
            # Validation simple
            required_fields = ['name', 'terrain_type', 'capacity', 'price_per_hour', 'status']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'success': False,
                        'error': f'Champ requis: {field}'
                    }, status=400)
            
            # Créer le terrain
            terrain = Terrain.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                terrain_type=data['terrain_type'],
                capacity=int(data['capacity']),
                price_per_hour=float(data['price_per_hour']),
                status=data['status'],
                image=data.get('image', '')
            )
            
            return JsonResponse({
                'success': True,
                'terrain': {
                    'id': terrain.id,
                    'name': terrain.name,
                    'description': terrain.description,
                    'terrain_type': terrain.terrain_type,
                    'capacity': terrain.capacity,
                    'price_per_hour': str(terrain.price_per_hour),
                    'status': terrain.status,
                    'average_rating': str(terrain.average_rating),
                    'image': terrain.image or ''
                }
            }, status=201)
            
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
    
    elif request.method == 'PUT':
        # Modifier un terrain existant
        try:
            data = json.loads(request.body)
            terrain_id = data.get('id')
            
            if not terrain_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID du terrain requis'
                }, status=400)
            
            try:
                terrain = Terrain.objects.get(id=terrain_id)
            except Terrain.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Terrain non trouvé'
                }, status=404)
            
            # Mettre à jour les champs
            if 'name' in data:
                terrain.name = data['name']
            if 'description' in data:
                terrain.description = data['description']
            if 'terrain_type' in data:
                terrain.terrain_type = data['terrain_type']
            if 'capacity' in data:
                terrain.capacity = int(data['capacity'])
            if 'price_per_hour' in data:
                terrain.price_per_hour = float(data['price_per_hour'])
            if 'status' in data:
                terrain.status = data['status']
            if 'image' in data:
                terrain.image = data['image']
            
            terrain.save()
            
            return JsonResponse({
                'success': True,
                'terrain': {
                    'id': terrain.id,
                    'name': terrain.name,
                    'description': terrain.description,
                    'terrain_type': terrain.terrain_type,
                    'capacity': terrain.capacity,
                    'price_per_hour': str(terrain.price_per_hour),
                    'status': terrain.status,
                    'average_rating': str(terrain.average_rating),
                    'image': terrain.image or ''
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
    
    elif request.method == 'DELETE':
        # Supprimer un terrain
        try:
            data = json.loads(request.body)
            terrain_id = data.get('id')
            
            if not terrain_id:
                return JsonResponse({
                    'success': False,
                    'error': 'ID du terrain requis'
                }, status=400)
            
            try:
                terrain = Terrain.objects.get(id=terrain_id)
                terrain_name = terrain.name
                terrain.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Terrain "{terrain_name}" supprimé avec succès'
                })
                
            except Terrain.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Terrain non trouvé'
                }, status=404)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)
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
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'Méthode non autorisée'
        }, status=405)

if __name__ == '__main__':
    print("Utilisation: Ajouter cette vue à votre URLs Django")
    print("Exemple: path('api/simple-terrains/', simple_terrain_api)")
