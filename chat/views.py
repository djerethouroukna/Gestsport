from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q, Count
from .models import ChatRoom, Message

User = get_user_model()

@login_required
def chat_room_list(request):
    """Liste des salons de chat de l'utilisateur"""
    chat_rooms = ChatRoom.objects.filter(
        participants=request.user
    ).select_related('created_by').prefetch_related('participants').annotate(
        unread_count=Count('messages', filter=Q(messages__read=False))
    )
    
    # Salons disponibles pour la création
    available_users = User.objects.exclude(id=request.user.id)
    
    context = {
        'chat_rooms': chat_rooms,
        'available_users': available_users,
    }
    return render(request, 'chat/chat_room_list.html', context)

@login_required
def chat_room(request, room_id):
    """Interface d'un salon de chat"""
    chat_room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    # Récupérer les messages avec pagination
    messages = chat_room.messages.select_related('author').order_by('created_at')
    
    # Autres salons pour la sidebar
    other_rooms = ChatRoom.objects.filter(
        participants=request.user
    ).exclude(id=room_id).annotate(
        unread_count=Count('messages', filter=Q(messages__read=False))
    )
    
    # Marquer les messages comme lus
    chat_room.messages.filter(read=False).exclude(author=request.user).update(read=True)
    
    context = {
        'chat_room': chat_room,
        'messages': messages,
        'other_rooms': other_rooms,
    }
    return render(request, 'chat/chat_room.html', context)

@login_required
@require_POST
def create_room(request):
    """Créer un nouveau salon de chat"""
    name = request.POST.get('name', '').strip()
    room_type = request.POST.get('room_type', 'group')
    participants_ids = request.POST.getlist('participants')
    
    if not name:
        messages.error(request, 'Le nom du salon est obligatoire')
        return redirect('chat:chat_room_list')
    
    # Créer le salon
    chat_room = ChatRoom.objects.create(
        name=name,
        room_type=room_type,
        created_by=request.user
    )
    
    # Ajouter le créateur comme participant
    chat_room.participants.add(request.user)
    
    # Ajouter les autres participants
    if participants_ids:
        participants = User.objects.filter(id__in=participants_ids)
        chat_room.participants.add(*participants)
    
    # Envoyer une notification aux nouveaux participants
    from notifications.utils import NotificationService
    for participant in participants:
        NotificationService.create_notification(
            recipient=participant,
            title='Nouveau salon de chat',
            message=f'Vous avez été ajouté au salon "{name}"',
            notification_type='system_message',
            content_object=chat_room
        )
    
    messages.success(request, f'Salon "{name}" créé avec succès')
    return redirect('chat:chat_room', room_id=chat_room.id)

@login_required
def test_chat(request):
    """Page de test pour le module chat"""
    return render(request, 'chat/test_chat.html')

@login_required
def api_chat_rooms(request):
    """API pour récupérer les salons de chat"""
    chat_rooms = ChatRoom.objects.filter(
        participants=request.user
    ).select_related('created_by').prefetch_related('participants').annotate(
        unread_count=Count('messages', filter=Q(messages__read=False))
    )
    
    rooms_data = []
    for room in chat_rooms:
        rooms_data.append({
            'id': room.id,
            'name': room.name,
            'room_type': room.room_type,
            'room_type_display': room.get_room_type_display(),
            'participants_count': room.participants.count(),
            'unread_count': room.unread_count,
            'last_activity': room.last_activity.isoformat() if room.last_activity else None,
            'created_by': room.created_by.get_full_name() or room.created_by.username,
        })
    
    return JsonResponse({'rooms': rooms_data})

@login_required
def api_send_message(request, room_id):
    """API pour envoyer un message dans un salon"""
    chat_room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({'error': 'Le message ne peut pas être vide'}, status=400)
        
        # Créer le message
        message = Message.objects.create(
            chatroom=chat_room,
            author=request.user,
            content=content
        )
        
        # Mettre à jour la dernière activité du salon
        from django.utils import timezone
        chat_room.last_activity = timezone.now()
        chat_room.save()
        
        # Retourner le message créé
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'author_id': message.author.id,
                'author_name': message.author.get_full_name() or message.author.username,
                'author_username': message.author.username,
                'created_at': message.created_at.isoformat(),
                'is_edited': message.is_edited,
            }
        })
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@login_required
def api_delete_message(request, message_id):
    """API pour supprimer un message (seulement si auteur)"""
    message = get_object_or_404(Message, id=message_id)
    
    # Vérifier que l'utilisateur est l'auteur du message
    if message.author != request.user:
        return JsonResponse({'error': 'Vous ne pouvez supprimer que vos propres messages'}, status=403)
    
    if request.method == 'POST' or request.method == 'DELETE':
        # Supprimer le message
        message.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Message supprimé avec succès'
        })
    
    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@login_required
def api_chat_messages(request, room_id):
    """API pour récupérer les messages d'un salon"""
    chat_room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    
    messages = chat_room.messages.select_related('author').order_by('created_at')
    
    messages_data = []
    for message in messages:
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'author_id': message.author.id,
            'author_name': message.author.get_full_name() or message.author.username,
            'author_username': message.author.username,
            'created_at': message.created_at.isoformat(),
            'is_edited': message.is_edited,
        })
    
    return JsonResponse({'messages': messages_data})
