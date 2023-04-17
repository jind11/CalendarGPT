import os
import pickle
from datetime import datetime

import pytz
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GoogleCalendar:
    def __init__(
        self,
        credentials_path=os.path.join(os.path.dirname(__file__), "my_credentials.json"),
    ):
        self.credentials = self.get_credentials(credentials_path)
        self.service = build("calendar", "v3", credentials=self.credentials)

    def get_credentials(self, credentials_path):
        creds = None
        scopes = ["https://www.googleapis.com/auth/calendar"]
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

    def list_events(self, attendee: str, date: str, timezone: str = "US/Pacific"):
        email = attendee
        date = datetime.strptime(date, "%Y-%m-%d")
        date_start = date.astimezone(pytz.timezone(timezone)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        date_end = date.astimezone(pytz.timezone(timezone)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        events_result = (
            # pylint: disable=no-member
            self.service.events()
            .list(
                calendarId=email,
                timeMin=date_start.isoformat(),
                timeMax=date_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            return "No events found."
        return events
