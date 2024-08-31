from functools import cached_property

import requests
from django.conf import settings
from django.utils import timezone

from project.models import Client, Project, TimeEntry



class Harvest:
    @cached_property
    def requester(self):
        session = requests.session()
        session.headers = {
            'Authorization': f'Bearer {settings.SYSTEM_CONFIG["harvest"]["access_token"]}',
            'Harvest-Account-Id': settings.SYSTEM_CONFIG["harvest"]["account_id"],
        }
        return session

    def get_clients(self):
        response = self.requester.get("https://api.harvestapp.com/v2/clients")
        clients_data = response.json()['clients']
        for client_data in clients_data:
            Client.objects.update_or_create(
                harvest_id=client_data['id'],
                defaults={'name': client_data['name']}
            )

    def get_projects(self):
        response = self.requester.get("https://api.harvestapp.com/v2/projects")
        projects_data = response.json()['projects']
        for project_data in projects_data:
            client, _ = Client.objects.get_or_create(harvest_id=project_data['client']['id'])
            Project.objects.update_or_create(
                harvest_id=project_data['id'],
                defaults={
                    'name': project_data['name'],
                    'description': project_data.get('notes'),
                    'client': client
                }
            )

    def get_time_entries(self, start_date, end_date):
        params = {
            'from': start_date.isoformat(),
            'to': end_date.isoformat()
        }
        response = self.requester.get("https://api.harvestapp.com/v2/time_entries", params=params)
        time_entries_data = response.json()['time_entries']
        for entry_data in time_entries_data:
            project = Project.objects.get(harvest_id=entry_data['project']['id'])
            TimeEntry.objects.update_or_create(
                harvest_id=entry_data['id'],
                defaults={
                    'project': project,
                    'date': entry_data['spent_date'],
                    'hours': timezone.timedelta(hours=entry_data['hours']),
                    'notes': entry_data['notes'],
                    'billable': entry_data['billable']
                }
            )

    def sync_all_data(self):
        self.get_clients()
        self.get_projects()
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=30)
        self.get_time_entries(start_date, end_date)

    def post_time_entry(self, time_entry):
        data = {
            "project_id": time_entry.project.harvest_id,
            "spent_date": time_entry.spent_date.isoformat(),
            "hours": str(time_entry.hours),
            "notes": time_entry.notes
        }
        response = self.requester.post("https://api.harvestapp.com/v2/time_entries", json=data)
        if response.status_code == 201:
            time_entry.harvest_id = response.json()['id']
            time_entry.save()
            return True
        return False

# Utility function to sync Harvest data
def sync_harvest_data():
    harvest = Harvest()
    harvest.sync_all_data()