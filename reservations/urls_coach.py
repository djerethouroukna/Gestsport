# reservations/urls_coach.py - URLs pour les fonctionnalités coach
from django.urls import path
from . import views_coach

app_name = 'reservations_coach'

urlpatterns = [
    # Dashboard coach
    path('dashboard/', views_coach.coach_reservation_dashboard, name='coach_dashboard'),
    
    # Gestion des réservations du coach
    path('reservations/', views_coach.CoachReservationListView.as_view(), name='reservation_list'),
    path('reservations/<int:pk>/', views_coach.CoachReservationDetailView.as_view(), name='reservation_detail'),
    path('reservations/<int:pk>/cancel/', views_coach.coach_cancel_reservation, name='cancel_reservation'),
    
    # Statistiques
    path('stats/', views_coach.coach_reservation_stats, name='stats'),
]
