from django.urls import path
from . import views
from . import orchestration_views
from . import views_admin

app_name = 'reservations'

urlpatterns = [
    # Vues principales
    path('', views.ReservationListView.as_view(), name='reservation_list'),
    path('create/', views.reservation_create_view, name='reservation_create'),
    path('from-activity/<int:activity_id>/', views.reservation_from_activity, name='reservation_from_activity'),
    path('<int:pk>/', views.ReservationDetailView.as_view(), name='reservation_detail'),
    path('<int:pk>/checkout/', views.payment_checkout, name='payment_checkout'),
    path('<int:pk>/edit/', views.ReservationUpdateView.as_view(), name='reservation_edit'),
    path('<int:pk>/cancel/', views.cancel_reservation, name='reservation_cancel'),
    path('<int:pk>/payment/success/', views.payment_success, name='payment_success'),
    path('<int:pk>/payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('calendar/', views.reservation_calendar, name='reservation_calendar'),
    
    # URLs pour les tickets (redirection vers tickets app)
    path('<int:reservation_id>/ticket/download/', views.download_ticket_redirect, name='download_ticket'),
    
    # Vues admin spécifiques
    path('admin/dashboard/', views_admin.admin_reservation_dashboard, name='admin_dashboard'),
    path('admin/list/', views_admin.admin_reservation_list, name='admin_reservation_list'),
    path('admin/<int:pk>/', views_admin.admin_reservation_detail, name='admin_reservation_detail'),
    path('admin/<int:pk>/edit/', views_admin.admin_reservation_edit, name='admin_reservation_edit'),
    
    # Template views orchestrées (système unifié)
    path('orchestrated/', orchestration_views.ReservationListViewOrchestrated.as_view(), name='reservation_list_orchestrated'),
    path('orchestrated/create/', orchestration_views.ReservationCreateOrchestratedView.as_view(), name='reservation_create_orchestrated'),
    path('orchestrated/<int:pk>/', orchestration_views.ReservationDetailOrchestratedView.as_view(), name='reservation_detail_orchestrated'),
    path('orchestrated/<int:pk>/confirmation/', orchestration_views.reservation_confirmation_view, name='reservation_confirmation'),
    path('orchestrated/<int:reservation_id>/cancel/', orchestration_views.cancel_reservation_view, name='cancel_reservation'),
    path('orchestrated/analytics/', orchestration_views.dashboard_analytics_view, name='dashboard_analytics'),
    
    # Actions AJAX pour les templates orchestrés
    path('check-availability/', orchestration_views.check_availability_view, name='check_availability'),
    
    # Actions de confirmation par entraîneur
    path('<int:reservation_id>/confirm/', views.confirm_reservation, name='reservation_confirm'),
    path('<int:reservation_id>/reject/', views.reject_reservation, name='reservation_reject'),
    path('<int:reservation_id>/approve-cancel/', views.approve_cancel, name='reservation_approve_cancel'),
    
    # Actions AJAX pour le dashboard admin
    path('admin/run-expired-check/', views_admin.run_expired_check, name='run_expired_check'),
    path('admin/mark-expired-completed/', views_admin.mark_expired_completed, name='mark_expired_completed'),
]
