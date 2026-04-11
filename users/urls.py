from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import debug_views

app_name = 'users'

urlpatterns = [
    # Authentification
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='users:login'), name='logout'),
    path('register/', views.PublicRegisterView.as_view(), name='register'),
    path('verify-email/<uidb64>/<token>/', views.EmailVerificationView.as_view(), name='email_verification'),
    path('admin/register/', views.RegisterView.as_view(), name='admin_register'),
    
    # Gestion du mot de passe
    path('password-reset/', 
         debug_views.DebugPasswordResetView.as_view(),
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
             success_url='/users/reset/done/'
         ), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    path('password-change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='users/password_change_done.html'
         ), 
         name='password_change_done'),
    
    # Profil utilisateur
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('settings/', views.settings_view, name='settings'),
    path('change-password/', views.change_password, name='change_password'),
    path('save-preferences/', views.save_preferences, name='save_preferences'),
    path('api/preferences/', views.api_preferences, name='api_preferences'),
    path('set-language/', views.set_language, name='set_language'),
    
    # Administration (accessible uniquement par les admins)
    path('', views.UserListView.as_view(), name='user_list'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('<int:pk>/edit/', views.UserEditView.as_view(), name='user_edit'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('<int:pk>/toggle-status/', views.UserToggleStatusView.as_view(), name='user_toggle_status'),
    
    # Actions rapides
    path('reservations/<int:user_id>/', views.UserReservationsView.as_view(), name='user_reservations'),
]
