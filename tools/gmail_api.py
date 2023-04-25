# prerequest
# pip install google-api-python-client
# pip install google-auth google-auth-oauthlib google-auth-httplib2

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import base64
import json
import os


class GmailClient:
    def __init__(self):
        self.credentials = self.get_credentials(credentials_path)
        self.service = self._create_gmail_service()

    def get_credentials(self, credentials_path):
        creds = None
        scopes = ['https://www.googleapis.com/auth/gmail.compose']
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

    def _create_gmail_service(self):
        # Authenticate and build the Gmail API client
        credentials = None
        token_path = os.path.join(os.path.dirname(__file__), "token.json")
        if os.path.exists(token_path):
            with open(token_path, "r") as token:
                credentials = json.load(token)

        if not credentials or not credentials.valid:
            SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(os.path.dirname(__file__), "emily_gmail_cred.json"), scopes=SCOPES)
            credentials = flow.run_local_server(port=0)

            # Save the credentials to a file
            with open(os.path.join(os.path.dirname(__file__), "token.json"), 'w') as f:
                f.write(credentials.to_json())
            
        service = build('gmail', 'v1', credentials=credentials)
        return service

    def send_email(self, input):
        input = json.loads(input)
        to, subject, body = input['recipient'], input['subject'], input['body']
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


if __name__ == "__main__":
    # for testing
    TestGmail = GmailClient()
    TestGmail.send_email("""{"recipient": "jindi930617@gmail.com", "subject": "test email 2", "body": "how are you?"}""")

