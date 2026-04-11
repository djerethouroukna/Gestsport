from django.urls import path
from . import views

app_name = 'terrains'

urlpatterns = [
    path('', views.terrain_list, name='terrain_list'),
    path('create/', views.terrain_create, name='terrain_create'),
    path('<int:terrain_id>/', views.terrain_detail, name='terrain_detail'),
    path('<int:terrain_id>/update/', views.terrain_update, name='terrain_update'),
    path('<int:terrain_id>/delete/', views.terrain_delete, name='terrain_delete'),
    path('<int:terrain_id>/quick-booking/', views.quick_booking, name='quick_booking'),
    path('<int:terrain_id>/availability/', views.terrain_availability, name='terrain_availability'),
    path('<int:terrain_id>/add-review/', views.add_review, name='add_review'),
]
