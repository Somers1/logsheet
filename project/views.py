import random
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import DetailView
from django.db.models import Min, Max
from datetime import timedelta
from collections import defaultdict

from project import models


class ProjectTimesheetListView(LoginRequiredMixin, DetailView):
    model = models.Project
    login_url = '/login/'
    redirect_field_name = 'next'
    template_name = 'timesheet.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(client__user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # if self.kwargs['month'] == 'all':
        #     context['event_blocks'] = context['project'].timeentry_set.all().order_by('-date')
        #     context['month'] = 'All Time'
        # else:
        if self.kwargs['month'] == 'current':
            start_date = timezone.now().astimezone(settings.AS_LOCAL_TIME_ZONE)
        else:
            start_date = timezone.datetime.strptime(
                self.kwargs['month'], '%Y-%m').astimezone(settings.AS_LOCAL_TIME_ZONE)
        context['month'] = start_date.strftime('%B %Y')
        context['event_blocks'] = context['project'].events_in_month(start_date.month, start_date.year)

        context['start_date'] = context['event_blocks'].aggregate(Min('date'))['date__min']
        context['end_date'] = context['event_blocks'].aggregate(Max('date'))['date__max']

        event_blocks_by_date = defaultdict(lambda: {'events': [], 'total_duration': timedelta()})
        total_duration = timedelta()
        total_billable = timedelta()
        for event in context['event_blocks']:
            date = event.date
            duration = event.hours
            if event.billable:
                total_billable += duration
            event_blocks_by_date[date]['events'].append({
                'duration': self.format_duration(duration),
                'summary': [part.strip() for part in event.notes.split('- ') if part.strip()],
                'billable': event.billable
            })
            event_blocks_by_date[date]['total_duration'] += duration
            total_duration += duration
        context['total_billable'] = self.format_duration(total_billable)
        for date, day_data in event_blocks_by_date.items():
            day_data['total_duration'] = self.format_duration(day_data['total_duration'])

        context['event_blocks_by_date'] = dict(event_blocks_by_date)

        current_month_start = timezone.now().astimezone(settings.AS_LOCAL_TIME_ZONE).replace(day=1).date()
        month_start = start_date.replace(day=1).date()
        context['remaining_hours'] = None
        if context['project'].monthly_duration:
            context['month_duration'] = self.format_duration(total_duration)
            carryover_hours = context['project'].carried_over_duration(month_start)
            context['carried_over'] = self.format_duration(carryover_hours)
            # context['total_duration'] = self.format_duration(total_duration)
            budget = timezone.timedelta(hours=0)
            if start_date.date() >= context['project'].project_start_date:
                budget = context['project'].monthly_duration
            context['total_budget'] = self.format_duration(budget)
            context['remaining_hours'] = self.format_duration(budget - total_billable - carryover_hours)
        if context['project'].total_duration:
            context['month_duration'] = self.format_duration(total_duration)
            total_before_time = context['project'].duration_before_time(month_start)
            total_with_time = total_before_time + total_duration
            context['total_duration'] = self.format_duration(total_with_time)
            context['total_budget'] = self.format_duration(context['project'].total_duration)
            context['remaining_hours'] = self.format_duration(context['project'].total_duration - total_with_time)
        context['project_months'] = list(context['project'].timeentry_set.dates('date', 'month', order='DESC'))
        if current_month_start not in context['project_months']:
            context['project_months'] = [current_month_start] + context['project_months']
        context['projects'] = self.get_object().client.project_set.all()
        context['greeting'] = self.get_greeting()
        return context

    def format_duration(self, duration):
        is_negative = duration.total_seconds() < 0
        duration = abs(duration)
        total_minutes = int(duration.total_seconds() / 60)
        hours, minutes = divmod(total_minutes, 60)

        if hours and minutes:
            formatted = f"{hours} hr {minutes} min"
        elif hours:
            formatted = f"{hours} hr"
        else:
            formatted = f"{minutes} min"

        return f"-{formatted}" if is_negative else formatted

    def get_greeting(self):
        greetings = [
            "Hello", "Welcome", "Salutations", "Hi"
        ]

        time_based_greetings = {
            "morning": ["Good Morning", "Guten Morgen"],
            "afternoon": ["Good Afternoon", "Guten Tag"]
        }
        current_hour = timezone.now().astimezone(settings.AS_LOCAL_TIME_ZONE).hour

        if 5 <= current_hour < 12:
            greetings.extend(time_based_greetings["morning"])
        elif 12 <= current_hour < 17:
            greetings.extend(time_based_greetings["afternoon"])

        return random.choice(greetings)
