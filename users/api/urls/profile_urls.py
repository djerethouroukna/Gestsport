from django.urls import path
from ..views.profile_views import (
    ProfileViewSet, user_search_view, 
    public_profile_view, delete_account_view
)

urlpatterns = [
    # Profile management
    path('profile/me/', ProfileViewSet.as_view({'get': 'me'}), name='profile_me'),
    path('profile/update/', ProfileViewSet.as_view({'put': 'update_profile', 'patch': 'update_profile'}), name='profile_update'),
    path('profile/upload-picture/', ProfileViewSet.as_view({'post': 'upload_picture'}), name='profile_upload_picture'),
    path('profile/delete-picture/', ProfileViewSet.as_view({'delete': 'delete_picture'}), name='profile_delete_picture'),
    
    # Search and public profiles
    path('search/', user_search_view, name='user_search'),
    path('public/<int:user_id>/', public_profile_view, name='public_profile'),
    
    # Account management
    path('delete-account/', delete_account_view, name='delete_account'),
]
