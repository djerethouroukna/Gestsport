# timeslots/permissions.py
from rest_framework import permissions


class CanViewTimeSlots(permissions.BasePermission):
    """Permission de voir les créneaux horaires"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin et coach peuvent voir tous les créneaux
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs peuvent voir les créneaux (consultation)
        return request.user.role == 'player'
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent voir tous les créneaux
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs peuvent voir tous les créneaux (consultation publique)
        return request.user.role == 'player'


class CanManageTimeSlots(permissions.BasePermission):
    """Permission de gérer les créneaux horaires"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Seuls admin et coach peuvent gérer les créneaux
        return request.user.role in ['admin', 'coach']
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent gérer tous les créneaux
        return request.user.role in ['admin', 'coach']


class CanBookTimeSlots(permissions.BasePermission):
    """Permission de réserver des créneaux"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Tous les utilisateurs peuvent réserver des créneaux
        return True
    
    def has_object_permission(self, request, view, obj):
        # Uniquement les créneaux disponibles peuvent être réservés
        return obj.can_be_booked


class CanManageAvailabilityRules(permissions.BasePermission):
    """Permission de gérer les règles de disponibilité"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Seuls admin et coach peuvent gérer les règles
        return request.user.role in ['admin', 'coach']
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent gérer toutes les règles
        return request.user.role in ['admin', 'coach']


class CanViewAvailabilityRules(permissions.BasePermission):
    """Permission de voir les règles de disponibilité"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin et coach peuvent voir toutes les règles
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs peuvent voir uniquement les règles actives
        return request.user.role == 'player'
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent voir toutes les règles
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs voient uniquement les règles actives
        return obj.is_active


class CanManageTimeSlotBlocks(permissions.BasePermission):
    """Permission de gérer les blocages de créneaux"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Seuls admin et coach peuvent gérer les blocages
        return request.user.role in ['admin', 'coach']
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent gérer tous les blocages
        return request.user.role in ['admin', 'coach']


class CanViewTimeSlotBlocks(permissions.BasePermission):
    """Permission de voir les blocages de créneaux"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin et coach peuvent voir tous les blocages
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs voient uniquement les blocages futurs
        return request.user.role == 'player'
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent voir tous les blocages
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs voient uniquement les blocages futurs
        from django.utils import timezone
        return obj.start_datetime >= timezone.now()


class CanGenerateTimeSlots(permissions.BasePermission):
    """Permission de générer des créneaux horaires"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Seuls admin et coach peuvent générer des créneaux
        return request.user.role in ['admin', 'coach']


class IsTimeSlotOwnerOrAdmin(permissions.BasePermission):
    """Permission d'accéder à un créneau (réservation associée ou admin)"""
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent accéder à tous les créneaux
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Le propriétaire de la réservation peut accéder au créneau
        if obj.reservation and obj.reservation.user == request.user:
            return True
        
        return False


class CanUpdateTimeSlotPrice(permissions.BasePermission):
    """Permission de modifier le prix d'un créneau"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Seuls admin et coach peuvent modifier les prix
        return request.user.role in ['admin', 'coach']
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent modifier tous les prix
        return request.user.role in ['admin', 'coach']
