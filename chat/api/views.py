from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from users.api.permissions.user_permissions import CanAccessChat, IsOwnerOrAdmin
from chat.models import ChatRoom, Message
from chat.serializers import ChatRoomSerializer, MessageSerializer

User = get_user_model()

class ChatRoomViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des salons de chat"""
    serializer_class = ChatRoomSerializer
    permission_classes = [CanAccessChat]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['room_type']
    search_fields = ['name']
    ordering_fields = ['created_at', 'last_activity']
    
    def get_queryset(self):
        """Filtrer les salons selon l'utilisateur"""
        user = self.request.user
        return ChatRoom.objects.filter(participants=user).order_by('-last_activity')
    
    def get_permissions(self):
        """Permissions selon l'action"""
        if self.action == 'create':
            return [CanAccessChat()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        else:  # list, retrieve
            return [CanAccessChat()]
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Rejoindre un salon de chat"""
        chatroom = self.get_object()
        user = request.user
        
        if chatroom.participants.filter(id=user.id).exists():
            return Response(
                {'error': 'Vous êtes déjà dans ce salon'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        chatroom.participants.add(user)
        return Response({
            'message': 'Vous avez rejoint le salon',
            'participants_count': chatroom.participants.count()
        })
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Quitter un salon de chat"""
        chatroom = self.get_object()
        user = request.user
        
        if not chatroom.participants.filter(id=user.id).exists():
            return Response(
                {'error': 'Vous n\'êtes pas dans ce salon'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        chatroom.participants.remove(user)
        return Response({
            'message': 'Vous avez quitté le salon',
            'participants_count': chatroom.participants.count()
        })

class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des messages"""
    serializer_class = MessageSerializer
    permission_classes = [CanAccessChat]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['chatroom']
    ordering = ['created_at']
    
    def get_queryset(self):
        """Filtrer les messages selon les salons de l'utilisateur"""
        user = self.request.user
        user_chatrooms = ChatRoom.objects.filter(participants=user)
        return Message.objects.filter(chatroom__in=user_chatrooms)
    
    def perform_create(self, serializer):
        """Assigner l'auteur lors de la création"""
        serializer.save(author=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_messages(self, request):
        """Récupérer les messages des salons de l'utilisateur"""
        user_chatrooms = ChatRoom.objects.filter(participants=request.user)
        messages = Message.objects.filter(chatroom__in=user_chatrooms).order_by('-created_at')
        
        # Pagination
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

@api_view(['GET'])
@permission_classes([CanAccessChat])
def my_chatrooms_view(request):
    """Récupérer les salons de chat de l'utilisateur"""
    chatrooms = ChatRoom.objects.filter(participants=request.user).order_by('-last_activity')
    serializer = ChatRoomSerializer(chatrooms, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([CanAccessChat])
def create_direct_message_view(request):
    """Créer un message direct avec un autre utilisateur"""
    target_user_id = request.data.get('user_id')
    
    if not target_user_id:
        return Response(
            {'error': 'ID utilisateur requis'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return Response(
            {'error': 'Utilisateur non trouvé'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier si un salon direct existe déjà
    existing_chatroom = ChatRoom.objects.filter(
        room_type='direct',
        participants=request.user
    ).filter(participants=target_user).first()
    
    if existing_chatroom:
        return Response({
            'message': 'Salon direct existant',
            'chatroom_id': existing_chatroom.id,
            'chatroom': ChatRoomSerializer(existing_chatroom).data
        })
    
    # Créer un nouveau salon direct
    chatroom = ChatRoom.objects.create(
        name=f"DM - {request.user.get_full_name()} & {target_user.get_full_name()}",
        room_type='direct',
        created_by=request.user
    )
    chatroom.participants.add(request.user, target_user)
    
    return Response({
        'message': 'Salon direct créé',
        'chatroom': ChatRoomSerializer(chatroom).data
    }, status=status.HTTP_201_CREATED)
