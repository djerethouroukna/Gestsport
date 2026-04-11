from rest_framework import permissions

class IsSelfOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj == request.user or request.user.is_staff

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'
        
class IsPlayer(permissions.BasePermission):
    """Permission pour les joueurs (PLAYER)"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'player'

class IsCoach(permissions.BasePermission):
    """Permission pour les entraîneurs (COACH)"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'coach'

class IsAdminOrCoach(permissions.BasePermission):
    """Permission pour les admins ou les entraîneurs"""
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and user.role in ['admin', 'coach']

class IsAdminOrPlayer(permissions.BasePermission):
    """Permission pour les admins ou les joueurs"""
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and user.role in ['admin', 'player']

class CanViewReservations(permissions.BasePermission):
    """Permission pour consulter les réservations"""
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and user.role in ['player', 'coach', 'admin']

class CanCreateReservation(permissions.BasePermission):
    """Permission pour créer des réservations (coach et admin)"""
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and user.role in ['coach', 'admin']

class CanValidateReservation(permissions.BasePermission):
    """Permission pour valider les réservations (admin uniquement)"""
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and user.role == 'admin'

class CanCreateActivity(permissions.BasePermission):
    """Permission pour créer des activités (coach et admin)"""
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and user.role in ['coach', 'admin']

class CanJoinActivity(permissions.BasePermission):
    """Permission pour s'inscrire à des activités (player, coach, admin)"""
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and user.role in ['player', 'coach', 'admin']

class CanManageUsers(permissions.BasePermission):
    """Permission pour gérer les utilisateurs (admin uniquement)"""
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and user.role == 'admin'

class CanAccessChat(permissions.BasePermission):
    """Permission pour accéder au chat (tous les rôles)"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission pour les propriétaires de ressources ou admin"""
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        # Vérifier si l'utilisateur est admin
        if user.role == 'admin':
            return True
        
        # Vérifier si l'utilisateur est propriétaire (à adapter selon l'objet)
        if hasattr(obj, 'user'):
            return obj.user == user
        elif hasattr(obj, 'created_by'):
            return obj.created_by == user
        elif hasattr(obj, 'owner'):
            return obj.owner == user
        
        return False