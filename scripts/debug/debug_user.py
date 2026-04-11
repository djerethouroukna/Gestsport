#!/usr/bin/env python3
"""
Page de test pour vérifier l'utilisateur connecté
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def debug_user(request):
    """Page de debug pour vérifier l'utilisateur connecté"""
    user = request.user
    html = f"""
    <h1>DEBUG UTILISATEUR</h1>
    <p><strong>Email:</strong> {user.email}</p>
    <p><strong>Rôle:</strong> {user.role}</p>
    <p><strong>is_staff:</strong> {user.is_staff}</p>
    <p><strong>is_active:</strong> {user.is_active}</p>
    <p><strong>is_authenticated:</strong> {user.is_authenticated}</p>
    
    <h2>URLs de test</h2>
    <ul>
        <li><a href="/dashboard/coach/">Dashboard Coach</a></li>
        <li><a href="/reservations/admin/dashboard/">Dashboard Réservations</a></li>
        <li><a href="/reservations/admin/list/">Liste Réservations</a></li>
        <li><a href="/admin/">Admin Django</a></li>
    </ul>
    
    <h2>Test d'accès direct</h2>
    <p>Essayez d'accéder directement à: <a href="/reservations/admin/dashboard/">/reservations/admin/dashboard/</a></p>
    """
    return HttpResponse(html)

# Pour ajouter cette URL temporairement, ajoutez dans config/urls.py:
# path('debug-user/', debug_user, name='debug_user'),
