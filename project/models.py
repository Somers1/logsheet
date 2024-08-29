import re
from django.conf import settings
from django.db import models
from django.utils import timezone

from project.importers import get_importer
from .agent import llm
from .calendar import AzureCalendarExport


def strip_before_dash(s):
    return '- ' + s.split('-', 1)[-1].strip()


class Client(models.Model):
    name = models.CharField(max_length=255)
    harvest_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    name = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    eraser_embed = models.TextField(null=True, blank=True)
    monthly_duration = models.DurationField(null=True, blank=True)
    total_duration = models.DurationField(null=True, blank=True)
    harvest_id = models.CharField(max_length=255, null=True, blank=True)

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

    def total_time_delta(self):
        return self.timeentry_set.aggregate(models.Sum('hours'))['hours__sum']

    def remaining_duration(self):
        return self.total_duration - self.total_time_delta()

    def summarise_missing(self):
        filters = models.Q(summary__isnull=True) | ~models.Q(summary__startswith='-')
        for event_block in self.eventblock_set.filter(filters).order_by('-start_timestamp'):
            event_block.summarise()

    def days_with_events(self):
        return {event.timestamp.astimezone(settings.AS_LOCAL_TIME_ZONE).date()
                for event in Event.objects.filter(source__project=self)}

    def create_days(self):
        for day in self.days_with_events():
            ProjectDaySummary.objects.get_or_create(project=self, date=day)

    def summarise_days(self):
        for day in self.projectdaysummary_set.filter(summary__isnull=True).order_by('date'):
            day.summarise()

    def add_all_to_harvest(self):
        for day in self.projectdaysummary_set.filter(summary__isnull=False).order_by('date'):
            day.add_to_harvest()

    def add_all_to_calendar(self):
        for event_block in self.eventblock_set.filter(uploaded_to_calendar=False).order_by('-start_timestamp'):
            event_block.add_to_calendar()


class TimeEntry(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    date = models.DateField()
    hours = models.DurationField()
    notes = models.TextField(null=True, blank=True)
    harvest_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.project} - {self.date} - {self.duration}"


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


class SourceRule(models.Model):
    EXACT = 'EXACT'
    CONTAINS = 'CONTAINS'
    STARTS_WITH = 'STARTS_WITH'
    END_WITH = 'END_WITH'
    REGEX = 'REGEX'

    RULE_TYPE_CHOICES = [
        (EXACT, EXACT.title()),
        (CONTAINS, CONTAINS.title()),
        (STARTS_WITH, STARTS_WITH.title()),
        (END_WITH, END_WITH.title()),
        (REGEX, REGEX.title())
    ]
    source = models.ForeignKey(Source, on_delete=models.CASCADE, choices=RULE_TYPE_CHOICES)
    rule_type = models.CharField(max_length=50)
    rule = models.TextField()

    def check_rule(self, event_text):
        if self.rule_type == self.EXACT:
            return self.rule == event_text
        if self.rule_type == self.CONTAINS:
            return self.rule in event_text
        if self.rule_type == self.STARTS_WITH:
            return event_text.startswith(self.rule)
        if self.rule_type == self.END_WITH:
            return event_text.endswith(self.rule)
        if self.rule_type == self.REGEX:
            return bool(re.match(self.rule, event_text))


class Event(models.Model):
    timestamp = models.DateTimeField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    event_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['timestamp', 'source', 'event_text'], name='unique_event')
        ]


class ProjectDaySummary(models.Model):
    summary = models.TextField(null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    date = models.DateField()
    uploaded_to_harvest = models.BooleanField(default=False)

    @property
    def start_timestamp(self):
        return timezone.datetime.combine(
            self.date, timezone.datetime.min.time()).astimezone(settings.AS_LOCAL_TIME_ZONE)

    @property
    def end_timestamp(self):
        return timezone.datetime.combine(
            self.date, timezone.datetime.max.time()).astimezone(settings.AS_LOCAL_TIME_ZONE)

    def event_blocks(self):
        return EventBlock.objects.filter(
            start_timestamp__range=[self.start_timestamp, self.end_timestamp],
            project=self.project
        ).order_by('start_timestamp')

    def total_hours(self):
        return sum(block.duration().total_seconds() for block in self.event_blocks()) / 3600

    def events(self):
        return Event.objects.filter(
            timestamp__range=[self.start_timestamp, self.end_timestamp],
            source__project=self.project
        ).order_by('timestamp')

    def joined_events_text(self):
        return '\n'.join([f'Source {event.source.source_type}: {event.event_text}' for event in self.events()])

    def summarise(self):
        prompt = f"""
        Here are the events that happened during my working session. 
        Please summarise what was done in a couple concise dot points.
        Do not use emails as events. Only use them as context. Do not print the source.
        Only reply with the dot points. Do no prefix your response with anything.

        Use this project description as context for the events: 
        {self.project.description}

        Events:
        {self.joined_events_text()}

        """
        self.summary = strip_before_dash(llm.strong.invoke(prompt).content)
        print(self.summary + '\n' + '-' * 50)
        self.save()

    def add_to_harvest(self):
        # Harvest().post_project_day(self)
        # self.uploaded_to_harvest = True
        # self.save()
        print(f'Added to {self} harvest')


class DurationBlock(models.Model):
    duration = models.DurationField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    summary = models.TextField(null=True)


class EventBlock(models.Model):
    start_timestamp = models.DateTimeField(null=True)
    end_timestamp = models.DateTimeField(null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True)
    summary = models.TextField(null=True)
    uploaded_to_calendar = models.BooleanField(default=False)

    @property
    def tz_start_timestamp(self):
        return self.start_timestamp.astimezone(settings.AS_LOCAL_TIME_ZONE)

    @property
    def tz_end_timestamp(self):
        return self.end_timestamp.astimezone(settings.AS_LOCAL_TIME_ZONE)

    def duration(self):
        return self.end_timestamp - self.start_timestamp

    def __str__(self):
        return f'{self.project} - {self.start_timestamp.astimezone(settings.AS_LOCAL_TIME_ZONE)} to' \
               f' {self.end_timestamp.astimezone(settings.AS_LOCAL_TIME_ZONE)}'

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
        Focus more on what was achieved rather than individual events. 
        Do not use emails as events. Only use them as context.
        Only reply with the dot points. Do no prefix your response with anything.
        Please make it as concise as you possible can only including the really important information.
                
        Use this project description as context for the events: 
        {self.project.description}
        
        Events:
        {self.joined_events_text()}
        
        """
        self.summary = strip_before_dash(llm.strong.invoke(prompt).content)
        print(self.summary + '\n' + '-' * 50)
        self.save()

    def add_to_calendar(self):
        AzureCalendarExport().add_event_block(self)
        self.uploaded_to_calendar = True
        self.save()
        print(f'Added to {self} calendar')
