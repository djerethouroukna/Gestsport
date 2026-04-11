# terrains/api/upload_views.py
import json
import base64
import uuid
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

@csrf_exempt
@require_http_methods(["POST"])
def upload_terrain_image(request):
    """
    Endpoint pour uploader une image de terrain
    Retourne l'URL de l'image sauvegardée
    """
    try:
        data = json.loads(request.body)
        image_data = data.get('image', '')
        
        if not image_data:
            return JsonResponse({'error': 'Aucune image fournie'}, status=400)
        
        # Vérifier si c'est du Base64
        if not image_data.startswith('data:image/'):
            return JsonResponse({'error': 'Format d\'image invalide'}, status=400)
        
        # Extraire le type et les données
        format, imgstr = image_data.split(';base64,')
        ext = format.split('/')[-1]
        
        # Valider l'extension
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        if ext.lower() not in allowed_extensions:
            return JsonResponse({'error': f'Extension {ext} non autorisée'}, status=400)
        
        # Générer un nom unique
        filename = f"terrain_{uuid.uuid4().hex[:8]}.{ext}"
        
        # Décoder et sauvegarder
        image_content = base64.b64decode(imgstr)
        path = default_storage.save(f'terrains/{filename}', ContentFile(image_content, name=filename))
        
        # URL de l'image
        image_url = request.build_absolute_uri(f'{settings.MEDIA_URL}{path}')
        
        return JsonResponse({
            'success': True,
            'image_url': image_url,
            'filename': filename
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
