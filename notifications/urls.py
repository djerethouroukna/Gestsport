from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('count/', views.notification_count_view, name='notification_count'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
]
