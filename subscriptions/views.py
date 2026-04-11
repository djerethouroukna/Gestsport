# subscriptions/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Membership, Subscription, CreditPackage, UserCredit


class MembershipViewSet(viewsets.ModelViewSet):
    """ViewSet pour les types d'abonnements"""
    queryset = Membership.objects.all()
    serializer_class = None  # À implémenter plus tard


class SubscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les abonnements utilisateurs"""
    queryset = Subscription.objects.all()
    serializer_class = None  # À implémenter plus tard


class CreditPackageViewSet(viewsets.ModelViewSet):
    """ViewSet pour les forfaits de crédits"""
    queryset = CreditPackage.objects.all()
    serializer_class = None  # À implémenter plus tard


class UserCreditViewSet(viewsets.ModelViewSet):
    """ViewSet pour les crédits utilisateurs"""
    queryset = UserCredit.objects.all()
    serializer_class = None  # À implémenter plus tard
