from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from project.models import Client, Project, TimeEntry


class ProjectCalculationsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'password')
        self.client = Client.objects.create(name='Test Client', user=self.user)
        self.project = Project.objects.create(
            name='Test Project',
            client=self.client,
            project_start_date=date(2024, 1, 15),
            monthly_duration=timedelta(hours=40),
            total_duration=timedelta(hours=500)
        )
    
    def test_events_in_month_filters_by_year(self):
        TimeEntry.objects.create(
            project=self.project,
            date=date(2023, 8, 15),
            hours=timedelta(hours=10),
            harvest_id='harvest_2023_aug',
            billable=True
        )
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 8, 15),
            hours=timedelta(hours=5),
            harvest_id='harvest_2024_aug',
            billable=True
        )
        
        events_2023 = self.project.events_in_month(8, 2023)
        events_2024 = self.project.events_in_month(8, 2024)
        
        self.assertEqual(events_2023.count(), 1)
        self.assertEqual(events_2024.count(), 1)
        self.assertEqual(events_2023.first().date.year, 2023)
        self.assertEqual(events_2024.first().date.year, 2024)
    
    def test_carried_over_duration_positive_carryover(self):
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 20),
            hours=timedelta(hours=30),
            harvest_id='harvest_jan',
            billable=True
        )
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 2, 20),
            hours=timedelta(hours=35),
            harvest_id='harvest_feb',
            billable=True
        )
        
        march_start = date(2024, 3, 1)
        carryover = self.project.carried_over_duration(march_start)
        
        # 2 months elapsed (Jan, Feb), budget = 80 hours
        # Used = 65 hours (30 + 35)
        # Carryover = 65 - 80 = -15 hours (15 hours remaining/positive carryover)
        self.assertEqual(carryover, timedelta(hours=-15))
    
    def test_carried_over_duration_negative_carryover(self):
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 20),
            hours=timedelta(hours=50),
            harvest_id='harvest_jan_over',
            billable=True
        )
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 2, 20),
            hours=timedelta(hours=45),
            harvest_id='harvest_feb_over',
            billable=True
        )
        
        march_start = date(2024, 3, 1)
        carryover = self.project.carried_over_duration(march_start)
        
        # 2 months elapsed, budget = 80 hours
        # Used = 95 hours (50 + 45)
        # Carryover = 95 - 80 = 15 hours (15 hours over budget/negative carryover)
        self.assertEqual(carryover, timedelta(hours=15))
    
    def test_carried_over_duration_ignores_non_billable(self):
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 20),
            hours=timedelta(hours=30),
            harvest_id='harvest_jan_billable',
            billable=True
        )
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 25),
            hours=timedelta(hours=20),
            harvest_id='harvest_jan_non_billable',
            billable=False
        )
        
        feb_start = date(2024, 2, 1)
        carryover = self.project.carried_over_duration(feb_start)
        
        # 1 month elapsed, budget = 40 hours
        # Billable used = 30 hours (non-billable ignored)
        # Carryover = 30 - 40 = -10 hours (10 hours remaining)
        self.assertEqual(carryover, timedelta(hours=-10))
    
    def test_carried_over_duration_project_starts_mid_month(self):
        # Project starts Jan 15, checking March 1
        march_start = date(2024, 3, 1)
        
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 20),
            hours=timedelta(hours=20),
            harvest_id='harvest_jan_mid',
            billable=True
        )
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 2, 10),
            hours=timedelta(hours=40),
            harvest_id='harvest_feb_mid',
            billable=True
        )
        
        carryover = self.project.carried_over_duration(march_start)
        
        # From Jan 1 to Mar 1 = 2 complete months
        # Budget = 80 hours (2 × 40)
        # Used = 60 hours (20 + 40)
        # Carryover = 60 - 80 = -20 hours (20 hours remaining)
        self.assertEqual(carryover, timedelta(hours=-20))
    
    def test_billable_duration_before_time(self):
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 20),
            hours=timedelta(hours=10),
            harvest_id='harvest_before_1',
            billable=True
        )
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 2, 15),
            hours=timedelta(hours=15),
            harvest_id='harvest_before_2',
            billable=False
        )
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 3, 10),
            hours=timedelta(hours=20),
            harvest_id='harvest_after',
            billable=True
        )
        
        march_start = date(2024, 3, 1)
        duration_before = self.project.billable_duration_before_time(march_start)
        
        # Only billable hours before March 1: 10 hours (15 non-billable ignored)
        self.assertEqual(duration_before, timedelta(hours=10))
    
    def test_duration_before_time_includes_all_hours(self):
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 20),
            hours=timedelta(hours=10),
            harvest_id='harvest_all_1',
            billable=True
        )
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 2, 15),
            hours=timedelta(hours=15),
            harvest_id='harvest_all_2',
            billable=False
        )
        
        march_start = date(2024, 3, 1)
        duration_before = self.project.duration_before_time(march_start)
        
        # All hours before March 1: 25 hours (10 + 15)
        self.assertEqual(duration_before, timedelta(hours=25))
    
    def test_carried_over_no_project_start_date(self):
        project_no_start = Project.objects.create(
            name='No Start Date Project',
            client=self.client,
            monthly_duration=timedelta(hours=40)
        )
        project_no_start.project_start_date = None
        project_no_start.save()
        
        march_start = date(2024, 3, 1)
        carryover = project_no_start.carried_over_duration(march_start)
        
        self.assertEqual(carryover, timedelta(0))
    
    def test_carried_over_no_monthly_duration(self):
        project_no_monthly = Project.objects.create(
            name='No Monthly Duration Project',
            client=self.client,
            project_start_date=date(2024, 1, 15)
        )
        project_no_monthly.monthly_duration = None
        project_no_monthly.save()
        
        march_start = date(2024, 3, 1)
        carryover = project_no_monthly.carried_over_duration(march_start)
        
        self.assertEqual(carryover, timedelta(0))
    
    def test_remaining_hours_with_positive_carryover(self):
        """Test remaining hours when we have unused hours from previous months"""
        # Setup: 30 hours used in Jan (under 40 hour budget)
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 20),
            hours=timedelta(hours=30),
            harvest_id='jan_under',
            billable=True
        )
        
        # February: use 25 hours
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 2, 15),
            hours=timedelta(hours=25),
            harvest_id='feb_current',
            billable=True
        )
        
        feb_start = date(2024, 2, 1)
        carryover = self.project.carried_over_duration(feb_start)
        
        # Carryover: 30 used - 40 budget = -10 (10 hours unused/positive carryover)
        self.assertEqual(carryover, timedelta(hours=-10))
        
        # Remaining in Feb: 40 budget + 10 unused - 25 used = 25 hours
        # Formula should be: budget - carryover - billable
        # = 40 - (-10) - 25 = 40 + 10 - 25 = 25
        remaining = self.project.monthly_duration - carryover - timedelta(hours=25)
        self.assertEqual(remaining, timedelta(hours=25))
    
    def test_remaining_hours_with_negative_carryover(self):
        """Test remaining hours when we've overused hours from previous months"""
        # Setup: 50 hours used in Jan (over 40 hour budget)
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 1, 20),
            hours=timedelta(hours=50),
            harvest_id='jan_over',
            billable=True
        )
        
        # February: use 25 hours
        TimeEntry.objects.create(
            project=self.project,
            date=date(2024, 2, 15),
            hours=timedelta(hours=25),
            harvest_id='feb_current_over',
            billable=True
        )
        
        feb_start = date(2024, 2, 1)
        carryover = self.project.carried_over_duration(feb_start)
        
        # Carryover: 50 used - 40 budget = 10 (10 hours overused/negative carryover)
        self.assertEqual(carryover, timedelta(hours=10))
        
        # Remaining in Feb: 40 budget - 10 overused - 25 used = 5 hours
        # Formula should be: budget - carryover - billable
        # = 40 - 10 - 25 = 5
        remaining = self.project.monthly_duration - carryover - timedelta(hours=25)
        self.assertEqual(remaining, timedelta(hours=5))