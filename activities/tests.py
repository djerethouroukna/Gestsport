from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, time, datetime

from .models import Activity, ActivityStatus
from terrains.models import Terrain, OpeningHours
from django.contrib.auth import get_user_model
from timeslots.services import TimeSlotService
from timeslots.models import TimeSlot, TimeSlotStatus

User = get_user_model()


class ActivityConfirmationTests(TestCase):
    def setUp(self):
        # Users
        self.coach = User.objects.create_user(email='coach@example.com', password='pass', role='coach')
        self.admin = User.objects.create_user(email='admin@example.com', password='pass', role='admin')

        # Terrain and opening hours
        self.terrain = Terrain.objects.create(
            name='Terrain Test',
            terrain_type='football',
            capacity=20,
            price_per_hour=20.00
        )

        # Choose a date in the future
        self.target_date = (timezone.now() + timedelta(days=2)).date()
        OpeningHours.objects.create(
            terrain=self.terrain,
            day_of_week=self.target_date.weekday(),
            opening_time=time(8, 0),
            closing_time=time(20, 0)
        )

        # Generate timeslots for that date
        TimeSlotService.generate_range_timeslots(self.terrain, self.target_date, self.target_date, duration_minutes=60)

        self.client = Client()

    def test_activity_creation_by_coach_does_not_block_timeslots(self):
        self.client.login(email='coach@example.com', password='pass')

        start_dt = datetime.combine(self.target_date, time(10, 0))
        end_dt = datetime.combine(self.target_date, time(12, 0))

        response = self.client.post(reverse('activities:activity_create'), data={
            'title': 'Training',
            'description': 'Session',
            'activity_type': 'training',
            'terrain': self.terrain.id,
            'max_participants': 10,
            'start_time': start_dt.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end_dt.strftime('%Y-%m-%dT%H:%M')
        })

        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.get(title='Training')
        self.assertEqual(activity.status, ActivityStatus.PENDING)

        # Ensure timeslots in interval are still available (not blocked)
        blocked_slots = TimeSlot.objects.filter(terrain=self.terrain, date=self.target_date, status=TimeSlotStatus.BLOCKED)
        self.assertEqual(blocked_slots.count(), 0)

    def test_admin_confirm_blocks_timeslots_and_confirms(self):
        # Create activity as coach first
        activity = Activity.objects.create(
            title='Training',
            description='Session',
            activity_type='training',
            terrain=self.terrain,
            coach=self.coach,
            max_participants=10,
            start_time=datetime.combine(self.target_date, time(10, 0)),
            end_time=datetime.combine(self.target_date, time(12, 0)),
            status=ActivityStatus.PENDING
        )

        # Admin confirms
        self.client.login(email='admin@example.com', password='pass')
        response = self.client.post(reverse('activities:activity_confirm', args=[activity.id]))
        self.assertEqual(response.status_code, 302)

        activity.refresh_from_db()
        self.assertEqual(activity.status, ActivityStatus.CONFIRMED)

        # Ensure timeslots in interval are now blocked
        blocked_slots = TimeSlot.objects.filter(
            terrain=self.terrain,
            date=self.target_date,
            start_time__gte=time(10, 0),
            end_time__lte=time(12, 0),
            status=TimeSlotStatus.BLOCKED
        )
        self.assertTrue(blocked_slots.exists())
