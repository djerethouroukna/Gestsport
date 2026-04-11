from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
import os

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la mise à jour du profil utilisateur"""
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'role',
            'phone', 'date_of_birth', 'address', 'city', 
            'postal_code', 'country', 'profile_picture'
        )
        read_only_fields = ('id', 'email', 'role')

    def validate_phone(self, value):
        """Validation du numéro de téléphone"""
        if value and not value.replace(' ', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Le numéro de téléphone doit contenir uniquement des chiffres.")
        return value

    def validate_profile_picture(self, value):
        """Validation de la photo de profil"""
        if value:
            # Vérifier la taille du fichier (max 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if value.size > max_size:
                raise serializers.ValidationError("L'image ne doit pas dépasser 5MB.")
            
            # Vérifier le type de fichier
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Seuls les formats JPEG, PNG, GIF et WebP sont autorisés."
                )
        return value

class ProfilePictureSerializer(serializers.ModelSerializer):
    """Sérialiseur spécifique pour l'upload de la photo de profil"""
    
    class Meta:
        model = User
        fields = ('profile_picture',)

    def validate_profile_picture(self, value):
        """Validation stricte de la photo de profil"""
        if not value:
            raise serializers.ValidationError("Une image est requise.")
        
        # Vérifier la taille (max 2MB pour l'avatar)
        max_size = 2 * 1024 * 1024  # 2MB
        if value.size > max_size:
            raise serializers.ValidationError("La photo de profil ne doit pas dépasser 2MB.")
        
        # Vérifier le type de fichier
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Seuls les formats JPEG, PNG et WebP sont autorisés pour la photo de profil."
            )
        
        return value

class PublicProfileSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les profils publics (informations limitées)"""
    
    class Meta:
        model = User
        fields = (
            'id', 'first_name', 'last_name', 'role', 
            'profile_picture', 'date_joined'
        )
        read_only_fields = ('id', 'first_name', 'last_name', 'role', 
                          'profile_picture', 'date_joined')

class ProfileSearchSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les résultats de recherche d'utilisateurs"""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'full_name', 'role', 'profile_picture', 'city')
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email
