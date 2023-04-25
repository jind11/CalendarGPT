import os
import pickle
from datetime import datetime
import json
import base64

import pytz
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText

GOOGLE_SERVICES_DICT = {'calendar': {'version': 'v3', 'scope': 'calendar'},
                        'gmail': {'version': 'v1', 'scope': 'gmail.compose'}}

class GoogleServices:
    def __init__(
        self,
        email,
        credentials_path=os.path.join(os.path.dirname(__file__), "emily_gmail_cred.json"),
        services=['calendar', 'gmail']
    ):
        self.email = email
        scopes = [f"https://www.googleapis.com/auth/{GOOGLE_SERVICES_DICT[service]['scope']}" for service in services]
        self.credentials = self.get_credentials(credentials_path, scopes)
        self.services = {}
        for service in services:
            self.services[service] = build(service, GOOGLE_SERVICES_DICT[service]['version'], credentials=self.credentials)

    def get_credentials(self, credentials_path, scopes):
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), "token.pickle")

        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if os.path.exists(credentials_path):
                    try:
                        creds = InstalledAppFlow.from_client_secrets_file(
                            credentials_path, scopes
                        )
                        creds = creds.run_local_server(port=0)
                    except FileNotFoundError:
                        print(f"Error: {credentials_path} not found.")

            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        return creds

    def list_events(self, dates: str, timezone: str = "US/Pacific"):
        events = []
        for date in dates.split(','):
            date = datetime.strptime(date, "%Y-%m-%d")
            date_start = date.astimezone(pytz.timezone(timezone)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            date_end = date.astimezone(pytz.timezone(timezone)).replace(
                hour=23, minute=59, second=59, microsecond=0
            )
            events_result = (
                # pylint: disable=no-member
                self.services['calendar'].events()
                .list(
                    calendarId=self.email,
                    timeMin=date_start.isoformat(),
                    timeMax=date_end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events.extend(events_result.get("items", []))

        if not events:
            return "No events found."
        return events

    def create_events(self, input: str, timezone: str = "America/Los_Angeles"):
        input = json.loads(input)
        recipients, event_summary, event_description, event_start_time, event_end_time = input['recipients'], input[
            'event_summary'], input['event_description'], input['event_start_time'], input['event_end_time']

        # event_start_time = datetime.strptime(event_start_time, "%Y-%m-%dT%H:%M:%S")
        # event_end_time = datetime.strptime(event_end_time, "%Y-%m-%dT%H:%M:%S")
        # Set the start and end time values using the datetime object
        event = {
            'summary': event_summary,
            'location': None,
            'description': event_description,
            'start': {
                'dateTime': event_start_time,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': event_end_time,
                'timeZone': timezone,
            },
            'attendees': [
                {'email': recipient} for recipient in recipients
            ],
            'reminders': {
                'useDefault': True,
            },
        }

        # Get the calendar ID
        calendar = self.services['calendar'].calendars().get(calendarId='primary').execute()
        calendar_id = calendar['id']

        # Add the event to the calendar
        try:
            execution_result = self.services['calendar'].events().insert(calendarId=calendar_id, body=event).execute()
            print(execution_result)
            return_message = 'Calendar invitation has been sent successfully!'
        except HttpError as error:
            return_message = 'Calendar invitation has failed to be sent!'

        return return_message


    def send_email(self, input):
        input = json.loads(input)
        recipients, subject, body = input['recipients'], input['subject'], input['body']
        assert isinstance(recipients, list), recipients
        try:
            # Create the message
            message = MIMEText(body)
            message['to'] = ','.join(recipients)
            message['subject'] = subject

            # Encode the message in base64
            create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

            # Send the message
            send_message = self.services['gmail'].users().messages().send(userId="me", body=create_message).execute()
            print(F'The message was sent to {recipients} with email Id: {send_message["id"]}')
            observation = F'The message was sent to {recipients} with email Id: {send_message["id"]}'

        except HttpError as error:
            print(F'An error occurred while sending email: {error}')
            observation = F'An error occurred while sending email: {error}'

        return observation

    def read_email(self, email_id):
        try:
            message = self.services['gmail'].users().messages().get(userId="me", id=email_id).execute()
            payload = message['payload']
            headers = payload['headers']
            subject = [header['value'] for header in headers if header['name'] == 'Subject'][0]
            sender = [header['value'] for header in headers if header['name'] == 'From'][0]
            date = [header['value'] for header in headers if header['name'] == 'Date'][0]
            body = self._get_email_body(payload)
            print(f'Subject: {subject}')
            print(f'From: {sender}')
            print(f'Date: {date}')
            print(f'Body: {body}')
        except HttpError as error:
            print(F'An error occurred while reading email: {error}')

    def check_unread_emails(self):
        try:
            unread_msgs = self.services['gmail'].users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD']).execute()
            return len(unread_msgs['messages'])
        except HttpError as error:
            print(F'An error occurred while checking unread emails: {error}')

    def _get_email_body(self, payload):
        if 'parts' in payload:
            parts = payload['parts']
            for part in parts:
                part_headers = part['headers']
                if any(header['name'] == 'Content-Type' and 'text/plain' in header['value'] for header in part_headers):
                    body = part['body']['data']
                    return base64.urlsafe_b64decode(body).decode()
        else:
            body = payload['body']['data']
            return base64.urlsafe_b64decode(body).decode()


if __name__ == "__main__":
    # for testing Gmail service
    # TestGmail = GoogleServices(email='emily.jarvis.assistant@gmail.com')
    # send_message = TestGmail.send_email("""{"recipients": ["jindi930617@gmail.com", "jindi15@mit.edu"], "subject": "test email 2", "body": "how are you?"}""")
    # print(send_message)

    # for testing calendar service
    # google_services = GoogleServices(email='emily.jarvis.assistant@gmail.com')
    # print(google_services.list_events('2023-05-01,2023-05-02'))

    # for testing calendar invitation service
    google_services = GoogleServices(email='emily.jarvis.assistant@gmail.com')
    print(google_services.create_events(
        """{"recipients": ["jindi930617@gmail.com"], "event_summary": "online meeting", "event_description": "discuss how to turn chatgpt", "event_start_time": "2023-04-25T10:30:00", "event_end_time": "2023-04-25T11:30:00"}"""))