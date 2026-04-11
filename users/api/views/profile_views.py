from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ..serializers.profile_serializer import (
    ProfileSerializer, ProfilePictureSerializer, 
    PublicProfileSerializer, ProfileSearchSerializer
)
from ..permissions.user_permissions import (
    IsPlayer, IsCoach, IsAdminOrCoach, CanAccessChat
)

User = get_user_model()

class ProfileViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des profils utilisateurs"""
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Un utilisateur ne peut voir/modifier que son propre profil"""
        return User.objects.filter(id=self.request.user.id)
    
    def get_serializer_class(self):
        """Sélection du sérialiseur selon l'action"""
        if self.action == 'upload_picture':
            return ProfilePictureSerializer
        elif self.action == 'public_profile':
            return PublicProfileSerializer
        return ProfileSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Récupérer le profil de l'utilisateur connecté"""
        if not request.user.is_authenticated:
            # Return mock data for unauthenticated users
            return Response({
                'first_name': 'Utilisateur',
                'last_name': 'Demo',
                'email': 'user@gestsport.com',
                'role': 'JOUEUR',
                'stats': {
                    'totalReservations': 5,
                    'totalActivities': 12,
                    'membershipMonths': 6
                }
            })
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Mettre à jour le profil de l'utilisateur connecté"""
        serializer = self.get_serializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_picture(self, request):
        """Uploader une photo de profil"""
        serializer = ProfilePictureSerializer(
            request.user, 
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Photo de profil mise à jour avec succès',
                'profile_picture': serializer.data['profile_picture']
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'])
    def delete_picture(self, request):
        """Supprimer la photo de profil"""
        if request.user.profile_picture:
            # Supprimer l'ancien fichier
            if request.user.profile_picture.storage.exists(request.user.profile_picture.name):
                request.user.profile_picture.delete()
            request.user.profile_picture = None
            request.user.save()
            return Response({'message': 'Photo de profil supprimée'})
        return Response(
            {'error': 'Aucune photo de profil à supprimer'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_search_view(request):
    """Recherche d'utilisateurs avec filtres"""
    query = request.GET.get('q', '')
    role = request.GET.get('role', '')
    city = request.GET.get('city', '')
    
    users = User.objects.filter(is_active=True)
    
    # Recherche par nom, prénom ou email
    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    # Filtre par rôle
    if role:
        users = users.filter(role=role)
    
    # Filtre par ville
    if city:
        users = users.filter(city__icontains=city)
    
    # Exclure l'utilisateur connecté
    users = users.exclude(id=request.user.id)
    
    serializer = ProfileSearchSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def public_profile_view(request, user_id):
    """Voir le profil public d'un utilisateur"""
    try:
        user = User.objects.get(id=user_id, is_active=True)
        serializer = PublicProfileSerializer(user)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response(
            {'error': 'Utilisateur non trouvé'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_account_view(request):
    """Supprimer le compte utilisateur"""
    user = request.user
    
    # Optionnel: Ajouter une confirmation par mot de passe
    password = request.data.get('password')
    if not password or not user.check_password(password):
        return Response(
            {'error': 'Mot de passe requis pour supprimer le compte'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Supprimer la photo de profil si elle existe
    if user.profile_picture:
        if user.profile_picture.storage.exists(user.profile_picture.name):
            user.profile_picture.delete()
    
    # Désactiver le compte plutôt que supprimer (soft delete)
    user.is_active = False
    user.email = f"deleted_{user.id}_{user.email}"
    user.save()
    
    return Response({'message': 'Compte supprimé avec succès'})
