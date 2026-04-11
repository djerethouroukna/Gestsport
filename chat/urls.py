from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Pages HTML
    path('', views.chat_room_list, name='chat_room_list'),
    path('room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('create/', views.create_room, name='create_room'),
    path('test/', views.test_chat, name='test_chat'),
    
    # API endpoints
    path('api/rooms/', views.api_chat_rooms, name='api_chat_rooms'),
    path('api/room/<int:room_id>/messages/', views.api_chat_messages, name='api_chat_messages'),
    path('api/room/<int:room_id>/send/', views.api_send_message, name='api_send_message'),
    path('api/message/<int:message_id>/delete/', views.api_delete_message, name='api_delete_message'),
]
