# payments/permissions.py
from rest_framework import permissions


class CanViewPayments(permissions.BasePermission):
    """Permission de voir les paiements"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin et coach peuvent voir tous les paiements
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs peuvent voir leurs propres paiements
        return request.user.role == 'player'
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent voir tous les paiements
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs peuvent voir uniquement leurs paiements
        return obj.user == request.user


class CanCreatePayment(permissions.BasePermission):
    """Permission de créer un paiement"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Seuls les joueurs peuvent créer des paiements
        # Admin et coach peuvent créer des paiements pour les réservations
        return request.user.role in ['player', 'admin', 'coach']


class CanManagePaymentMethods(permissions.BasePermission):
    """Permission de gérer les moyens de paiement"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Tous les utilisateurs authentifiés peuvent gérer leurs moyens de paiement
        return True
    
    def has_object_permission(self, request, view, obj):
        # Uniquement le propriétaire peut gérer ses moyens de paiement
        return obj.user == request.user


class CanProcessRefunds(permissions.BasePermission):
    """Permission de traiter les remboursements"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Seuls admin et coach peuvent traiter les remboursements
        return request.user.role in ['admin', 'coach']
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent traiter tous les remboursements
        return request.user.role in ['admin', 'coach']


class CanViewPaymentStatistics(permissions.BasePermission):
    """Permission de voir les statistiques de paiement"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin et coach peuvent voir toutes les statistiques
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Les joueurs peuvent voir uniquement leurs statistiques
        return request.user.role == 'player'


class IsPaymentOwnerOrAdmin(permissions.BasePermission):
    """Permission d'accéder à un paiement (propriétaire ou admin)"""
    
    def has_object_permission(self, request, view, obj):
        # Admin et coach peuvent accéder à tous les paiements
        if request.user.role in ['admin', 'coach']:
            return True
        
        # Le propriétaire peut accéder à son paiement
        return obj.user == request.user


class CanSimulatePayments(permissions.BasePermission):
    """Permission de simuler des paiements"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # En mode développement, tout le monde peut simuler
        # En production, seul admin peut simuler
        from django.conf import settings
        
        if getattr(settings, 'DEBUG', False):
            return True
        
        return request.user.role == 'admin'
