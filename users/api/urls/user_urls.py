from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views.user_views import UserViewSet, UserPublicViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'users-public', UserPublicViewSet, basename='user-public')

urlpatterns = [
    path('', include(router.urls)),
]