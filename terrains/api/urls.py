from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TerrainViewSet, TerrainPublicViewSet, check_multiple_availability, terrain_types
from .upload_views import upload_terrain_image

router = DefaultRouter()
router.register(r'terrains', TerrainViewSet, basename='terrain')
router.register(r'terrains-public', TerrainPublicViewSet, basename='terrain-public')

urlpatterns = [
    path('', include(router.urls)),
    path('check-availability/', check_multiple_availability, name='check_multiple_availability'),
    path('types/', terrain_types, name='terrain_types'),
    path('upload/terrain-image/', upload_terrain_image, name='upload_terrain_image'),
]
