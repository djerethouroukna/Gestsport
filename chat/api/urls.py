from django.urls import path, include
from rest_framework.routers import DefaultRouter
from chat.api.views import ChatRoomViewSet, MessageViewSet, my_chatrooms_view, create_direct_message_view

router = DefaultRouter()
router.register(r'chatrooms', ChatRoomViewSet, basename='chatroom')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
    path('my/', my_chatrooms_view, name='my_chatrooms'),
    path('direct/', create_direct_message_view, name='create_direct_message'),
]
