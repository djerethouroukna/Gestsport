"""

URL configuration for config project.



The `urlpatterns` list routes URLs to views. For more information please see:

    https://docs.djangoproject.com/en/4.2/topics/http/urls/

Examples:

Function views

    1. Add an import:  from my_app import views

    2. Add a URL to urlpatterns:  path('', views.home, name='home')

Class-based views

    1. Add an import:  from other_app.views import Home

    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')

Including another URLconf

    1. Import the include() function: from django.urls import include, path

    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""

from django.contrib import admin

from django.urls import path, include

from django.contrib.auth import views as auth_views

from users import views as user_views

from django.shortcuts import redirect

from django.conf import settings

from django.conf.urls.static import static

from . import views

from scripts.maintenance import admin_notifications

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from payments import views_invoice



urlpatterns = [

    path('admin/', admin.site.urls),

    

    # Page de test

    path('test-reservation/', views.test_reservation_view, name='test_reservation'),

    path('debug-user/', lambda request: __import__('debug_user').debug_user(request), name='debug_user'),

    path('debug-session/', views.debug_session_view, name='debug_session'),

    

    # Pages principales

    path('', views.home_view, name='home'),  # Page d'accueil

    path('dashboard/admin/', views.dashboard_admin_view, name='dashboard_admin'),

    path('dashboard/debug/', views.debug_chart_view, name='debug_chart'),

    path('dashboard/coach/', views.dashboard_coach_view, name='dashboard_coach'),

    path('dashboard/player/', views.dashboard_player_view, name='dashboard_player'),

    

    # Route directe pour les coachs (contourne le problème)

    path('coach/reservations/', views.coach_reservations_redirect, name='coach_reservations'),

    

    # Pages statiques

    path('about/', views.about_view, name='about'),

    path('contact/', views.contact_view, name='contact'),

    

    # Modules avec préfixes

    path('reservations/', include('reservations.urls')),  # Réservations avec préfixe

    path('reservations/admin/', include('reservations.urls_admin')),  # Admin réservations

    path('reservations/coach/', include('reservations.urls_coach')),  # Coach réservations

    path('tickets/', include('tickets.urls')),  # Tickets et scan

    path('terrains/', include('terrains.urls')),  # Templates pour terrains

    path('activities/', include('activities.urls')),  # Templates pour activités

    path('chat/', include('chat.urls')),  # Templates pour le chat

    path('users/', include('users.urls')),  # Templates pour les utilisateurs

    path('notifications/', include('notifications.urls')),  # Templates pour les notifications

    path('audit/', include('audit.urls')),  # Système d'audit

    path('reports/', include('reports.urls')),  # Rapports et exportations

    

    # Notifications admin

    path('admin/notifications/', admin_notifications.admin_notifications_view, name='admin_notifications'),

    path('admin/notifications/count/', admin_notifications.get_unread_count, name='admin_notifications_count'),

    

    # Authentification

    path('login/', user_views.CustomLoginView.as_view(), name='login'),

    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    path('déconnexion/', lambda request: redirect('/logout/')),  # Redirection vers /logout/

    path('accounts/login/', lambda request: redirect('/login/')),  # Redirection vers /login/

    

    # API endpoints

    path('api/auth/', include(('users.api.urls.auth_urls', 'users_api'), namespace='users_api')),  # Authentification JWT (namespaced)

    path('api/auth/', include('rest_framework.urls')),  # Pour l'authentification par session

    path('api/users/', include('users.api.urls.user_urls')),  # Nos URLs d'API

    path('api/users/', include('users.api.urls.profile_urls')),  # Gestion profil

    path('api/users/', include('users.api.urls.integration_urls')),  # Intégration modules

    path('api/terrains/', include('terrains.api.urls')),  # Terrains

    path('api/reservations/', include('reservations.api.urls')),  # Réservations

    path('api/activities/', include('activities.api.urls')),  # Activités

    path('api/chat/', include('chat.api.urls')),  # Chat

    path('api/notifications/', include('notifications.api.urls')),  # Notifications

    path('api/payments/', include('payments.urls_api')),  # API Paiements

    path('payments/', include('payments.urls')),  # Templates et historique des paiements

    path('payments/facture/<str:invoice_number>/', views_invoice.invoice_detail, name='invoice_detail'),

    path('payments/facture/<str:invoice_number>/download/', views_invoice.invoice_download, name='invoice_download'),

    path('payments/mes-factures/', views_invoice.invoice_list, name='invoice_list'),

    path('payments/admin/factures/', views_invoice.admin_invoice_list, name='admin_invoice_list'),

    path('payments/admin/facture/<str:invoice_number>/regenerate/', views_invoice.admin_regenerate_invoice, name='admin_regenerate_invoice'),

    path('payments/admin/facture/<str:invoice_number>/resend/', views_invoice.admin_resend_invoice, name='admin_resend_invoice'),

    path('api/timeslots/', include('timeslots.urls')),  # Créneaux horaires

    path('api/pricing/', include('pricing.urls')),  # Tarification dynamique

    path('api/subscriptions/', include('subscriptions.urls')),  # Abonnements

    path('api/waitinglist/', include('waitinglist.urls')),  # Liste d'attente

    path('api/scanner/scan/', views.ScannerAPIView.as_view(), name='scanner_scan'),

    

    # Documentation API

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

]



# Servir les fichiers médias en développement

if settings.DEBUG:

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
