from django.urls import path, include
from rest_framework.routers import DefaultRouter
from activities.api.views import ActivityViewSet, my_activities_view, all_activities_view
from activities.api.calendar_views import (
    activity_calendar_view, activity_conflicts_view, 
    activity_availability_summary, available_slots_view
)
from activities.api.stats_views import (
    activity_statistics_view, coach_statistics_view,
    terrain_statistics_view, participation_trends_view
)

router = DefaultRouter()
router.register(r'', ActivityViewSet, basename='activity')

urlpatterns = [
    path('', include(router.urls)),
    path('my/', my_activities_view, name='my_activities'),
    path('all/', all_activities_view, name='all_activities'),
    path('calendar/', activity_calendar_view, name='activity_calendar'),
    path('conflicts/', activity_conflicts_view, name='activity_conflicts'),
    path('availability/', activity_availability_summary, name='activity_availability'),
    path('available-slots/', available_slots_view, name='available_slots'),
    path('statistics/', activity_statistics_view, name='activity_statistics'),
    path('statistics/coach/<int:coach_id>/', coach_statistics_view, name='coach_statistics'),
    path('statistics/coach/', coach_statistics_view, name='my_coach_statistics'),
    path('statistics/terrain/<int:terrain_id>/', terrain_statistics_view, name='terrain_statistics'),
    path('statistics/terrain/', terrain_statistics_view, name='all_terrain_statistics'),
    path('trends/participation/', participation_trends_view, name='participation_trends'),
]
