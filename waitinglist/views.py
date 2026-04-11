# waitinglist/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import WaitingList, WaitingListConfiguration, WaitingListNotification


class WaitingListViewSet(viewsets.ModelViewSet):
    """ViewSet pour la liste d'attente"""
    queryset = WaitingList.objects.all()
    serializer_class = None  # À implémenter plus tard


class WaitingListConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet pour la configuration de la liste d'attente"""
    queryset = WaitingListConfiguration.objects.all()
    serializer_class = None  # À implémenter plus tard


class WaitingListNotificationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les notifications de la liste d'attente"""
    queryset = WaitingListNotification.objects.all()
    serializer_class = None  # À implémenter plus tard
