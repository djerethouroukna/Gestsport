# pricing/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import DynamicPricingRule, Holiday, PriceHistory


class DynamicPricingRuleViewSet(viewsets.ModelViewSet):
    """ViewSet pour les règles de tarification dynamique"""
    queryset = DynamicPricingRule.objects.all()
    serializer_class = None  # À implémenter plus tard


class HolidayViewSet(viewsets.ModelViewSet):
    """ViewSet pour les jours fériés"""
    queryset = Holiday.objects.all()
    serializer_class = None  # À implémenter plus tard


class PriceHistoryViewSet(viewsets.ModelViewSet):
    """ViewSet pour l'historique des prix"""
    queryset = PriceHistory.objects.all()
    serializer_class = None  # À implémenter plus tard
