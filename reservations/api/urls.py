from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReservationViewSet, my_reservations_view, all_reservations_view
from .calendar_views import calendar_view, terrain_availability_summary, available_slots, reservation_conflicts
from .payment_views import simulate_payment, payment_history, request_payment, payment_statistics
from .orchestration_views import (
    create_complete_reservation, cancel_reservation, get_reservation_details,
    check_availability_and_pricing, get_user_reservations_summary
)
from .analytics_views import (
    dashboard_summary, terrain_analytics, user_analytics,
    revenue_analytics, occupancy_analytics, quick_stats
)

router = DefaultRouter()
router.register(r'reservations', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),
    path('my/', my_reservations_view, name='my_reservations'),
    path('all/', all_reservations_view, name='all_reservations'),
    path('calendar/', calendar_view, name='calendar'),
    path('availability/', terrain_availability_summary, name='availability_summary'),
    path('available-slots/', available_slots, name='available_slots'),
    path('conflicts/', reservation_conflicts, name='reservation_conflicts'),
    path('payment/simulate/<int:reservation_id>/', simulate_payment, name='simulate_payment'),
    path('payment/history/', payment_history, name='payment_history'),
    path('payment/request/<int:reservation_id>/', request_payment, name='request_payment'),
    path('payment/statistics/', payment_statistics, name='payment_statistics'),
    
    # Endpoints d'orchestration unifiés
    path('orchestration/create/', create_complete_reservation, name='create_complete_reservation'),
    path('orchestration/cancel/<int:reservation_id>/', cancel_reservation, name='cancel_reservation'),
    path('orchestration/details/<int:reservation_id>/', get_reservation_details, name='get_reservation_details'),
    path('orchestration/check/', check_availability_and_pricing, name='check_availability_and_pricing'),
    path('orchestration/summary/', get_user_reservations_summary, name='get_user_reservations_summary'),
    
    # Endpoints d'analytics
    path('analytics/dashboard/', dashboard_summary, name='dashboard_summary'),
    path('analytics/terrain/<int:terrain_id>/', terrain_analytics, name='terrain_analytics'),
    path('analytics/user/', user_analytics, name='user_analytics'),
    path('analytics/user/<int:user_id>/', user_analytics, name='user_analytics_by_id'),
    path('analytics/revenue/', revenue_analytics, name='revenue_analytics'),
    path('analytics/occupancy/', occupancy_analytics, name='occupancy_analytics'),
    path('analytics/quick-stats/', quick_stats, name='quick_stats'),
]
