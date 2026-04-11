from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from ..serializers.auth_serializer import (
    LoginSerializer, RegisterSerializer, ChangePasswordSerializer,
    ResetPasswordSerializer, ResetPasswordConfirmSerializer
)

User = get_user_model()

def get_tokens_for_user(user):
    """Génère les tokens JWT pour un utilisateur"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    """Endpoint pour récupérer l'utilisateur actuel"""
    return Response({
        'id': request.user.id,
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'role': request.user.role,
        'is_active': request.user.is_active,
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """Endpoint de connexion"""
    serializer = LoginSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        
        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_active': user.is_active,
            }
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    """Endpoint d'inscription"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        
        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_active': user.is_active,
            },
            'message': 'Inscription réussie'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET','POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Endpoint de déconnexion

    GET  -> déconnexion de session (utile pour le browsable API)
    POST -> déconnexion JWT (blacklist du refresh token)
    """
    try:
        if request.method == 'GET':
            # Logout session (useful for browsable API or accidental GET requests)
            from django.contrib.auth import logout as django_logout
            django_logout(request)
            return Response({'message': 'Déconnexion de la session réussie'}, status=status.HTTP_200_OK)

        # POST: blacklist refresh token (JWT logout)
        refresh_token = request.data.get("refresh")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Déconnexion réussie'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Erreur lors de la déconnexion'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    """Endpoint pour changer le mot de passe"""
    serializer = ChangePasswordSerializer(
        data=request.data, 
        context={'request': request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Mot de passe changé avec succès'}, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password_view(request):
    """Endpoint pour demander la réinitialisation du mot de passe"""
    serializer = ResetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Générer le token et l'UID
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Envoyer l'email (à adapter selon vos besoins)
        reset_link = f"{settings.FRONTEND_URL}/reset-password-confirm/{uid}/{token}/"
        
        try:
            send_mail(
                'Réinitialisation de votre mot de passe',
                f'Voici le lien pour réinitialiser votre mot de passe: {reset_link}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response({'message': 'Email de réinitialisation envoyé'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Erreur lors de l\'envoi de l\'email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password_confirm_view(request):
    """Endpoint pour confirmer la réinitialisation du mot de passe"""
    serializer = ResetPasswordConfirmSerializer(data=request.data)
    if serializer.is_valid():
        try:
            uid = serializer.validated_data['uid']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            if default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({'message': 'Mot de passe réinitialisé avec succès'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Token invalide'}, status=status.HTTP_400_BAD_REQUEST)
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Lien de réinitialisation invalide'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
