import csv
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

import requests
from django.utils import timezone
from msal import ConfidentialClientApplication


class BaseImporter(ABC):
    def __init__(self, source):
        self.source = source
        self.batch = []

    @abstractmethod
    def fetch_events(self):
        pass

    def sync(self):
        self.fetch_events()
        self.source.event_set.bulk_create(self.batch, ignore_conflicts=True)
        self.batch = []
        self.update_last_sync()

    def save_event(self, event_text: str, timestamp: datetime):
        self.batch.append(self.source.event_set.model(
            source=self.source,
            event_text=event_text,
            timestamp=timestamp
        ))

    def update_last_sync(self):
        self.source.last_sync = timezone.now()
        self.source.save()


class GitHubImporter(BaseImporter):
    def fetch_events(self):
        headers = {"Authorization": f"token {self.source.api_key}"}
        url = self.source.base_url
        while url:
            response = requests.get(url, headers=headers)
            commits = response.json()
            for commit in commits:
                self.save_event(commit['commit']['message'], commit['commit']['author']['date'])
            url = response.links.get('next', {}).get('url')


class AzureImporter(BaseImporter):
    def fetch_events(self):
        for file_path in Path('media/azure').glob('*.csv'):
            self.process_csv_file(file_path)

    def process_csv_file(self, file_path):
        with file_path.open('r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                event_text = '\n'.join(f'{key}: {value}' for key, value in row.items())
                self.save_event(event_text, row['Time'])


class AWSImporter(BaseImporter):
    def fetch_events(self):
        pass


class JiraImporter(BaseImporter):
    def fetch_events(self):
        pass


class SlackImporter(BaseImporter):
    def fetch_events(self):
        pass


class OutlookImporter(BaseImporter):
    def __init__(self, source):
        super().__init__(source)
        self.access_token = self._get_access_token()

    def _get_access_token(self):
        app = ConfidentialClientApplication(
            self.source.auth_dict['client_id'],
            authority=f"https://login.microsoftonline.com/{self.source.auth_dict['tenant_id']}",
            client_credential=self.source.auth_dict['client_secret'],
        )
        result = app.acquire_token_silent(["https://graph.microsoft.com/.default"], account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception(f"Error acquiring token: {result.get('error')}")

    def fetch_events(self):
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        url = f"https://graph.microsoft.com/v1.0/users/{self.source.auth_dict['email']}/messages"
        params = {
            '$select': 'subject,receivedDateTime,bodyPreview,from,toRecipients,ccRecipients',
            '$orderby': 'receivedDateTime DESC',
            '$top': 50  # Adjust this value based on how many emails you want to fetch at once
        }
        while url:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            for email in data['value']:
                try:
                    from_email = email['from']['emailAddress']['address']
                    to_emails = [recipient['emailAddress']['address'] for recipient in email['toRecipients']]
                    cc_emails = [recipient['emailAddress']['address'] for recipient in email['ccRecipients']]
                    event_text = (
                        f"Subject: {email['subject']}\n"
                        f"From: {from_email}\n"
                        f"To: {', '.join(to_emails)}\n"
                        f"CC: {', '.join(cc_emails)}\n"
                        f"Body: {email['bodyPreview']}"
                    )
                    self.save_event(event_text, email['receivedDateTime'])
                except Exception as e:
                    print(f'Error saving email: {e}')
            url = data.get('@odata.nextLink')
            params = {}


def get_importer(source) -> BaseImporter:
    importers = {
        'github': GitHubImporter,
        'azure': AzureImporter,
        'aws': AWSImporter,
        'jira': JiraImporter,
        'slack': SlackImporter,
        'outlook': OutlookImporter,
    }
    importer_class = importers.get(source.source_type)
    if importer_class:
        return importer_class(source)
    else:
        raise ValueError(f"No importer found for source type: {source.source_type}")
