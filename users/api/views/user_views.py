from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.db.models import Q
from users.api.serializers.user_serializer import UserSerializer, UserDetailSerializer
from users.api.permissions.user_permissions import IsSelfOrAdmin, IsAdminUser

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        """Un utilisateur ne peut voir que son propre profil sauf admin"""
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all()
        return User.objects.filter(id=user.id)
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserSerializer
        return UserDetailSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = []
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsSelfOrAdmin]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

# UserViewSet public pour AppWorking (sans authentification)
class UserPublicViewSet(viewsets.ModelViewSet):
    """
    ViewSet public pour les utilisateurs - accessible sans authentification
    Pour développement et démonstration avec AppWorking
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserDetailSerializer
    permission_classes = [AllowAny]  # Pas d'authentification requise
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserSerializer
        return UserDetailSerializer
    
    def get_queryset(self):
        """Retourne tous les utilisateurs avec filtrage optionnel"""
        queryset = User.objects.all().order_by('-date_joined')
        
        # Filtrage par recherche
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filtrage par rôle
        role = self.request.query_params.get('role', None)
        if role and role != 'all':
            queryset = queryset.filter(role=role)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Retourne la liste des utilisateurs avec pagination"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Format de réponse compatible avec AppWorking
            return self.get_paginated_response({
                'users': serializer.data,
                'total': queryset.count()
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'users': serializer.data,
            'total': queryset.count()
        })
    
    def create(self, request, *args, **kwargs):
        """Créer un nouvel utilisateur (public pour AppWorking)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)