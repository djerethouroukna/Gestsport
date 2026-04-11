# timeslots/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TimeSlotViewSet, AvailabilityRuleViewSet, TimeSlotGenerationViewSet,
    TimeSlotBlockViewSet, search_timeslots, bulk_block_timeslots
)

router = DefaultRouter()
router.register(r'timeslots', TimeSlotViewSet, basename='timeslot')
router.register(r'availability-rules', AvailabilityRuleViewSet, basename='availability-rule')
router.register(r'generations', TimeSlotGenerationViewSet, basename='timeslot-generation')
router.register(r'blocks', TimeSlotBlockViewSet, basename='timeslot-block')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', search_timeslots, name='timeslot_search'),
    path('bulk-block/', bulk_block_timeslots, name='bulk_block_timeslots'),
]
