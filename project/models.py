from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone
from langchain_core.tools import tool

from project.importers import get_importer
from .agent import Agent, llm
import utils


class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def group_event_blocks(self):
        event_block = EventBlock()
        for event in Event.objects.filter(source__project=self).order_by('timestamp'):
            if not event_block.check_add_event(event):
                event_block.save()
                event_block = EventBlock()

    def total_seconds(self):
        return sum(event_block.duration().total_seconds() for event_block in self.eventblock_set.all())

    def total_hours(self):
        return self.total_seconds() / 3600

    def summarise_missing(self):
        for event_block in self.eventblock_set.filter(summary__isnull=True).order_by('-start_timestamp'):
            event_block.summarise()


class Timesheet(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    prompt = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    daily_html_format = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.project} | {self.start_time} - {self.end_time}'

    @property
    def days(self):
        return utils.DateRangeIterator(self.start_time, self.end_time)

    def generate(self, replace=False):
        for day in self.days:
            timesheet_day, _ = self.timesheetday_set.get_or_create(date=day.date(), timesheet=self)
            if replace or not timesheet_day.html:
                timesheet_day.generate()


class TimesheetDay(models.Model):
    date = models.DateField()
    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE)
    html = models.TextField(null=True, blank=True)

    @property
    def utc_end_time(self):
        return self.utc_start_time + timezone.timedelta(days=1)

    @property
    def utc_start_time(self):
        return timezone.datetime.combine(
            self.date, timezone.datetime.min.time()).astimezone(settings.AS_LOCAL_TIME_ZONE)

    def events(self):
        return Event.objects.filter(
            timestamp__range=[self.utc_start_time, self.utc_end_time],
            source__in=self.timesheet.project.source_set.filter(enabled=True)
        ).order_by('timestamp')

    def joined_events_text(self):
        return '\n'.join(
            [f'{event.source.source_type} | {event.timestamp}: {event.event_text}' for event in self.events()])

    def generate(self):
        if not self.events().exists():
            return print(f'No events found for this day {self.date}')
        prompt = f"""{self.timesheet.prompt}\n\n
        Project description: {self.timesheet.project.description}\n\n
        Events:\n{self.joined_events_text()}\n\n
        Please save using save_html with in the following format:\n\n 
        {self.timesheet.daily_html_format}"""

        @tool
        def save_html(html: str):
            """Save the html to the response field"""
            self.html = html
            self.save()

        agent = Agent([save_html])
        agent.invoke(prompt)
        print(f'Generated HTML for {self.date}')


class Source(models.Model):
    SOURCE_TYPES = [
        ('github', 'GitHub'),
        ('azure', 'Azure'),
        ('aws', 'AWS'),
        ('jira', 'Jira'),
        ('slack', 'Slack'),
        ('outlook', 'Outlook'),
    ]

    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    auth_dict = models.JSONField(blank=True, null=True)
    base_url = models.URLField(blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.source_type} - {self.project}'

    def sync(self):
        importer = get_importer(self)
        importer.sync()
        print(f'Synced {self.source_type} for {self.project}')


class Event(models.Model):
    timestamp = models.DateTimeField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    event_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['timestamp', 'source', 'event_text'], name='unique_event')
        ]


class EventBlock(models.Model):
    start_timestamp = models.DateTimeField(null=True)
    end_timestamp = models.DateTimeField(null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    summary = models.TextField(null=True)

    def duration(self):
        return self.end_timestamp - self.start_timestamp

    @property
    def task_end_time(self):
        try:
            return self.end_timestamp + timezone.timedelta(minutes=settings.TIMESHEET['time_on_task_minutes'])
        except TypeError:
            return None

    def add_event(self, event):
        if not self.start_timestamp:
            self.start_timestamp = event.timestamp
        if not self.project:
            self.project = event.source.project
        if not self.end_timestamp:
            self.end_timestamp = event.timestamp + timezone.timedelta(
                minutes=settings.TIMESHEET['minimum_task_minutes'])
        else:
            self.end_timestamp = event.timestamp

    def check_add_event(self, event):
        if not self.task_end_time or event.timestamp < self.task_end_time:
            self.add_event(event)
            return True

    def events(self):
        return Event.objects.filter(
            timestamp__range=[self.start_timestamp, self.end_timestamp],
            source__project=self.project
        ).order_by('timestamp')

    def joined_events_text(self):
        return '\n'.join([f'{event.source.source_type}: {event.event_text}' for event in self.events()])

    def summarise(self):
        prompt = f"""
        Here are the events that happened during my working session. 
        Please summarise the events in dot points that will be added to a timesheet and sent to the client.
        Focus more on what was achieved rather than individual events and make it as concise as possible. 
        Only reply with the dot points. Do no prefix your response with anything.
                
        Use this project description as context for the events: 
        {self.project.description}
        
        Events:
        {self.joined_events_text()}
        
        """
        self.summary = llm.strong.invoke(prompt).content
        print(self.joined_events_text())
        print(self.summary)
        self.save()
