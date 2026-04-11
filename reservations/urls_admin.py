# reservations/urls_admin.py - URLs pour les fonctionnalités admin
from django.urls import path
from . import views_admin

app_name = 'reservations_admin'

urlpatterns = [
    # Dashboard admin réservations
    path('dashboard/', views_admin.admin_reservation_dashboard, name='admin_dashboard'),
    
    # URLs admin pour la gestion des réservations expirées
    path('run-expired-check/', views_admin.run_expired_check, name='run_expired_check'),
    path('mark-expired-completed/', views_admin.mark_expired_completed, name='mark_expired_completed'),
    
    # URLs admin pour la gestion des réservations
    path('list/', views_admin.admin_reservation_list, name='list'),
    path('<int:pk>/', views_admin.admin_reservation_detail, name='detail'),
    path('<int:pk>/edit/', views_admin.admin_reservation_edit, name='edit'),
]
