app_name = 'users_api'

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from ..views.auth_views import (
    login_view, register_view, logout_view, current_user_view,
    change_password_view, reset_password_view, reset_password_confirm_view
)

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('me/', current_user_view, name='current_user'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('change-password/', change_password_view, name='change_password'),
    path('reset-password/', reset_password_view, name='reset_password'),
    path('reset-password-confirm/', reset_password_confirm_view, name='reset_password_confirm'),
]
