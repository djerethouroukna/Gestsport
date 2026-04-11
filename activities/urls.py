from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('', views.activity_list, name='activity_list'),
    path('create/', views.activity_create, name='activity_create'),
    path('<int:pk>/', views.activity_detail, name='activity_detail'),
    path('<int:pk>/join/', views.activity_join, name='activity_join'),
    path('<int:pk>/leave/', views.activity_leave, name='activity_leave'),
    path('<int:pk>/update/', views.activity_update, name='activity_update'),
    path('<int:pk>/delete/', views.activity_delete, name='activity_delete'),
    path('<int:pk>/confirm/', views.activity_confirm, name='activity_confirm'),
    path('<int:activity_id>/reserve/', views.activity_reservation_create, name='activity_reservation_create'),
    path('planning/', views.unified_planning, name='unified_planning'),
]
