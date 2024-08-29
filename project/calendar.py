import time

import requests
import msal
from django.conf import settings


class AzureCalendarExport:
    def __init__(self):
        calendar_settings = settings.SYSTEM_CONFIG['calendar']
        self.CLIENT_ID = calendar_settings['CLIENT_ID']
        self.CLIENT_SECRET = calendar_settings['CLIENT_SECRET']
        self.TENANT_ID = calendar_settings['TENANT_ID']
        self.USER_ID = calendar_settings['USER_ID']
        self.CALENDAR_ID = calendar_settings['CALENDAR_ID']
        self.AUTHORITY = f'https://login.microsoftonline.com/{self.TENANT_ID}'
        self.SCOPE = ['https://graph.microsoft.com/.default']
        self.ENDPOINT = 'https://graph.microsoft.com/v1.0'
        self._access_token = None

    def get_access_token(self):
        app = msal.ConfidentialClientApplication(
            self.CLIENT_ID, authority=self.AUTHORITY,
            client_credential=self.CLIENT_SECRET
        )
        result = app.acquire_token_silent(self.SCOPE, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=self.SCOPE)
        return result['access_token']

    @property
    def token(self):
        if self._access_token is None:
            self._access_token = self.get_access_token()
        return self._access_token

    @property
    def requester(self):
        session = requests.session()
        session.headers = {'Authorization': f'Bearer {self.token}'}
        return session

    def get_calendars(self):
        response = self.requester.get(f'{self.ENDPOINT}/users/{self.USER_ID}/calendars')
        response.raise_for_status()
        return response.json()['value']

    def update_event(self, updated_event):
        response = self.requester.post(
            f'{self.ENDPOINT}/users/{self.USER_ID}/calendars/{self.CALENDAR_ID}/events', json=updated_event)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def format_event_block(event_block):
        return {
            'subject': event_block.summary,
            'body': {
                'contentType': 'HTML',
                'content': 'This meeting was automatically generated by logsheet'
            },
            'start': {
                'dateTime': event_block.start_timestamp.astimezone(
                    settings.AS_LOCAL_TIME_ZONE).strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': "AUS Eastern Standard Time"
            },
            'end': {
                'dateTime': event_block.end_timestamp.astimezone(
                    settings.AS_LOCAL_TIME_ZONE).strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': "AUS Eastern Standard Time"
            }
        }

    def list_events(self):
        response = self.requester.get(
            f'{self.ENDPOINT}/users/{self.USER_ID}/calendars/{self.CALENDAR_ID}/events')
        response.raise_for_status()
        return response.json()['value']

    def delete_event(self, event_id):
        response = self.requester.delete(
            f'{self.ENDPOINT}/users/{self.USER_ID}/calendars/{self.CALENDAR_ID}/events/{event_id}')
        response.raise_for_status()
        return response.status_code == 204

    def clear_calendar(self):
        events = self.list_events()
        total_events = len(events)
        deleted_count = 0

        for event in events:
            if self.delete_event(event['id']):
                deleted_count += 1
                print(f"Deleted event: {event['subject']} ({deleted_count}/{total_events})")
            else:
                print(f"Failed to delete event: {event['subject']}")

        print(f"Deleted {deleted_count} out of {total_events} events.")

    def add_event_block(self, event_block):
        self.update_event(self.format_event_block(event_block))