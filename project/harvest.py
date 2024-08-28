from functools import cached_property

import requests
from django.conf import settings


class Harvest:
    @cached_property
    def requester(self):
        session = requests.session()
        session.headers = {
            'Authorization': f'Bearer {settings.SYSTEM_CONFIG["harvest"]["access_token"]}',
            'Harvest-Account-Id': settings.SYSTEM_CONFIG["harvest"]["account_id"],
        }
        return session

    def format_event(self, project_day):
        return {
            "project_id": self.get_project_id(project_day),
            "task_id": self.get_task_id(project_day),
            "spent_date": project_day.date.isoformat(),
            "hours": project_day.total_hours(),
            "notes": project_day.summary
        }

    def post_project_day(self, project_day):
        return self.post_event(self.format_event(project_day))

    def post_event(self, event):
        return self.requester.post("https://api.harvestapp.com/v2/time_entries", json=event)

    def get_task_id(self, project_day):
        for task in self.requester.get("https://api.harvestapp.com/v2/tasks").json()['tasks']:
            if task['name'].lower() == 'logsheet':
                return task['id']

    def get_project_id(self, project_day):
        for project in self.requester.get("https://api.harvestapp.com/v2/projects").json()['projects']:
            if project['name'].lower() == project_day.project.name.lower():
                return project['id']
