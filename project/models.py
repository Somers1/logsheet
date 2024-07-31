from pathlib import Path

from django.db import models
from langchain_core.tools import tool

from project.importers import get_importer
from .agent import Agent, llm


class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Timesheet(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    prompt = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    response = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.project} | {self.start_time} - {self.end_time}'

    def generate(self):
        events = Event.objects.filter(
            timestamp__range=[self.start_time, self.end_time], source__project=self.project).order_by('timestamp')
        event_texts = '\n'.join([f'{event.timestamp}: {event.event_text}' for event in events])
        prompt = f"""{self.prompt}\n\nEvents:\n{event_texts}\n\n
        Please save using save_html with times with an estimated total for each day and a summary of work done."""

        @tool
        def save_html(html: str):
            """Save the html to the response field"""
            self.response = html
            self.save()

        agent = Agent([save_html])
        agent.invoke(prompt)

    def save_html_file(self):
        path = Path('media', 'time_sheets')
        path.mkdir(parents=True, exist_ok=True)
        file_name = path / f'{self.project}_{self.start_time.isoformat()}_{self.end_time.isoformat()}.html'
        with open(file_name, 'w') as file:
            file.write(self.response)


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

    def __str__(self):
        return f'{self.source_type} - {self.project}'

    def sync(self):
        importer = get_importer(self)
        importer.sync()


class Event(models.Model):
    timestamp = models.DateTimeField()
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    event_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['timestamp', 'source', 'event_text'], name='unique_event')
        ]
