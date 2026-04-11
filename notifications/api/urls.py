from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notifications.api.views import (
    NotificationViewSet, my_notifications_view, unread_notifications_view, 
    unread_count_view, mark_all_as_read_view, clear_read_notifications_view
)

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('my/', my_notifications_view, name='my_notifications'),
    path('my/unread/', unread_notifications_view, name='unread_notifications'),
    path('unread_count/', unread_count_view, name='unread_count'),
    path('mark_all_read/', mark_all_as_read_view, name='mark_all_read'),
    path('clear_read/', clear_read_notifications_view, name='clear_read'),
]
