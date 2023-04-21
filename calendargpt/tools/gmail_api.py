# prerequest
# pip install google-api-python-client
# pip install google-auth google-auth-oauthlib google-auth-httplib2

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import base64


class GmailClient:
    def __init__(self):
        self.service = self._create_gmail_service()

    def _create_gmail_service(self):
        # Authenticate and build the Gmail API client
        SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
        flow = InstalledAppFlow.from_client_secrets_file(
            '/Users/Yuan/Desktop/SchedulePA/desktop_credentials.json', scopes=SCOPES)
        credentials = flow.run_local_server(port=0)

        # Save the credentials to a file
        with open('token.json', 'w') as f:
            f.write(credentials.to_json())
            
        service = build('gmail', 'v1', credentials=credentials)
        return service

    def send_email(self, to, subject, body):
        try:
            # Create the message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            # Encode the message in base64
            create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

            # Send the message
            send_message = (self.service.users().messages().send(userId="me", body=create_message).execute())
            print(F'The message was sent to {to} with email Id: {send_message["id"]}')

        except HttpError as error:
            print(F'An error occurred while sending email: {error}')
            send_message = None

        return send_message

    def read_email(self, email_id):
        try:
            message = self.service.users().messages().get(userId="me", id=email_id).execute()
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
            unread_msgs = self.service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD']).execute()
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

# TestGmail = GmailClient()

# TestGmail.send_email("bodiyuan@berkeley.edu", "test email 2", "how are you?")

