from django.conf import settings
from django.utils import timezone
from django.views.generic import ListView, DetailView
from django.db.models import Min, Max
from datetime import timedelta
from collections import defaultdict
from project import models


class ProjectTimesheetListView(DetailView):
    model = models.Project
    template_name = 'timesheet.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.kwargs['month'] == 'all':
            context['event_blocks'] = context['project'].timeentry_set.all().order_by('-date')
            context['month'] = 'All'
        else:
            if self.kwargs['month'] == 'current':
                start_date = timezone.now().astimezone(settings.AS_LOCAL_TIME_ZONE)
            else:
                start_date = timezone.datetime.strptime(
                    self.kwargs['month'], '%Y-%m').astimezone(settings.AS_LOCAL_TIME_ZONE)
            context['month'] = start_date.strftime('%B %Y')
            context['event_blocks'] = context['project'].timeentry_set.filter(
                date__month=start_date.month).order_by('-date')

        context['start_date'] = context['event_blocks'].aggregate(Min('date'))['date__min']
        context['end_date'] = context['event_blocks'].aggregate(Max('date'))['date__max']

        event_blocks_by_date = defaultdict(lambda: {'events': [], 'total_duration': timedelta()})
        total_duration = timedelta()

        for event in context['event_blocks']:
            date = event.date
            duration = event.hours
            event_blocks_by_date[date]['events'].append({
                'duration': self.format_duration(duration),
                'summary': [part.strip() for part in event.notes.split('- ') if part.strip()]
            })
            event_blocks_by_date[date]['total_duration'] += duration
            total_duration += duration

        for date, day_data in event_blocks_by_date.items():
            day_data['total_duration'] = self.format_duration(day_data['total_duration'])

        context['event_blocks_by_date'] = dict(event_blocks_by_date)
        context['total_duration'] = self.format_duration(total_duration)

        context['remaining_hours'] = None
        if context['project'].monthly_duration:
            context['month_duration'] = self.format_duration(total_duration)
            context['total_duration'] = self.format_duration(total_duration)
            context['total_budget'] = self.format_duration(context['project'].monthly_duration)
            context['remaining_hours'] = self.format_duration(
                context['project'].monthly_duration - total_duration)
        if context['project'].total_duration:
            context['month_duration'] = self.format_duration(total_duration)
            context['total_duration'] = self.format_duration(context['project'].total_time_delta())
            context['total_budget'] = self.format_duration(context['project'].total_duration)
            context['remaining_hours'] = self.format_duration(context['project'].remaining_duration())

        return context

    def format_duration(self, duration):
        total_minutes = int(duration.total_seconds() / 60)
        hours, minutes = divmod(total_minutes, 60)
        if hours and minutes:
            return f"{hours} hr {minutes} min"
        elif hours:
            return f"{hours} hr"
        return f"{minutes} min"
