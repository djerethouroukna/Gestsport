from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from users.api.permissions.user_permissions import IsOwnerOrAdmin
from notifications.models import Notification, NotificationPreference
from notifications.serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationListSerializer, UnreadCountSerializer,
    BulkNotificationSerializer, NotificationSearchSerializer
)

User = get_user_model()

class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['notification_type', 'priority', 'is_read']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Un utilisateur ne voit que ses notifications"""
        return Notification.objects.filter(recipient=self.request.user)
    
    def get_serializer_class(self):
        """Sélection du sérialiseur selon l'action"""
        if self.action == 'create':
            return NotificationCreateSerializer
        elif self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer
    
    def get_permissions(self):
        """Permissions selon l'action"""
        if self.action == 'create':
            return [IsOwnerOrAdmin()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marquer une notification comme lue"""
        notification = self.get_object()
        notification.mark_as_read()
        
        return Response({
            'message': 'Notification marquée comme lue',
            'is_read': notification.is_read,
            'read_at': notification.read_at
        })
    
    @action(detail=True, methods=['post'])
    def mark_as_unread(self, request, pk=None):
        """Marquer une notification comme non lue"""
        notification = self.get_object()
        notification.is_read = False
        notification.read_at = None
        notification.save()
        
        return Response({
            'message': 'Notification marquée comme non lue',
            'is_read': notification.is_read
        })
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Action en masse sur les notifications"""
        serializer = BulkNotificationSerializer(data=request.data)
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            action_type = serializer.validated_data['action']
            
            notifications = Notification.objects.filter(
                id__in=notification_ids,
                recipient=request.user
            )
            
            if action_type == 'mark_read':
                notifications.update(is_read=True, read_at=timezone.now())
                message = f"{notifications.count()} notifications marquées comme lues"
            elif action_type == 'mark_unread':
                notifications.update(is_read=False, read_at=None)
                message = f"{notifications.count()} notifications marquées comme non lues"
            elif action_type == 'delete':
                count = notifications.count()
                notifications.delete()
                message = f"{count} notifications supprimées"
            
            return Response({'message': message})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Rechercher des notifications"""
        serializer = NotificationSearchSerializer(data=request.GET)
        if serializer.is_valid():
            query = serializer.validated_data
            
            notifications = Notification.objects.filter(recipient=request.user)
            
            # Filtres
            if query.get('query'):
                notifications = notifications.filter(
                    Q(title__icontains=query['query']) |
                    Q(message__icontains=query['query'])
                )
            
            if query.get('notification_type'):
                notifications = notifications.filter(
                    notification_type=query['notification_type']
                )
            
            if query.get('priority'):
                notifications = notifications.filter(priority=query['priority'])
            
            if query.get('is_read') is not None:
                notifications = notifications.filter(is_read=query['is_read'])
            
            if query.get('date_from'):
                notifications = notifications.filter(
                    created_at__gte=query['date_from']
                )
            
            if query.get('date_to'):
                notifications = notifications.filter(
                    created_at__lte=query['date_to']
                )
            
            # Pagination
            page = self.paginate_queryset(notifications.order_by('-created_at'))
            if page is not None:
                serializer = NotificationListSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = NotificationListSerializer(notifications, many=True)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_notifications_view(request):
    """Récupérer les notifications de l'utilisateur connecté"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    
    # Pagination
    page_size = request.GET.get('page_size', 20)
    page = request.GET.get('page', 1)
    
    start = (int(page) - 1) * int(page_size)
    end = start + int(page_size)
    
    notifications_page = notifications[start:end]
    
    serializer = NotificationListSerializer(notifications_page, many=True)
    
    return Response({
        'results': serializer.data,
        'count': notifications.count(),
        'next': int(page) + 1 if end < notifications.count() else None,
        'previous': int(page) - 1 if int(page) > 1 else None
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_notifications_view(request):
    """Récupérer les notifications non lues"""
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')
    
    serializer = NotificationListSerializer(notifications, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_count_view(request):
    """Compter les notifications non lues"""
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    total_count = Notification.objects.filter(
        recipient=request.user
    ).count()
    
    serializer = UnreadCountSerializer({
        'unread_count': unread_count,
        'total_count': total_count
    })
    
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_as_read_view(request):
    """Marquer toutes les notifications comme lues"""
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return Response({'message': 'Toutes les notifications ont été marquées comme lues'})

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def clear_read_notifications_view(request):
    """Supprimer toutes les notifications lues"""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=True
    ).delete()[0]
    
    return Response({'message': f'{count} notifications lues ont été supprimées'})
