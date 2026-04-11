from django.urls import path
from ..views.integration_views import (
    user_reservations_view, user_activities_view, 
    user_dashboard_view, user_calendar_view, 
    user_stats_view, UserActivityViewSet
)

urlpatterns = [
    # Dashboard et intégration
    path('dashboard/', user_dashboard_view, name='user_dashboard'),
    path('reservations/', user_reservations_view, name='user_reservations'),
    path('activities/', user_activities_view, name='user_activities'),
    path('calendar/', user_calendar_view, name='user_calendar'),
    path('stats/', user_stats_view, name='user_stats'),
    
    # Activités détaillées (ViewSet)
    path('activities/', UserActivityViewSet.as_view({'get': 'list'}), name='user_activities_list'),
    path('activities/participating/', UserActivityViewSet.as_view({'get': 'participating'}), name='user_participating_activities'),
    path('activities/coaching/', UserActivityViewSet.as_view({'get': 'coaching'}), name='user_coaching_activities'),
]
