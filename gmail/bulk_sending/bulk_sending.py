import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import re
import pandas as pd

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def service_gmail():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service


def build_MIME(sender, to, subject, text):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    msg = MIMEText(text)
    message.attach(msg)

    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    return {'raw': raw}


def send_email(service, sender, to, subject, message_text):
    try:
        message = build_MIME(sender, to, subject, message_text)
        message = service.users().messages().send(userId="me", body=message).execute()
        print(f"Message Id: {message['id']}")
    except Exception as error:
        print(f'An error occurred: {error}')


def get_email_fields():
    try:
        with open('message.txt') as file:
            text = file.read()
    except Exception as error:
        print(f'The file message.txt could not be read due to the following error {error}')

    _from = re.search(r'\*from:"(.*?)"', text)
    if _from:
        _from = _from.group(1)
        print('From: ', _from)
    else:
        print('"From" not found')

    subject = re.search(r'\*subject:"(.*?)"', text)
    if subject:
        subject = subject.group(1)
        print("Subject:", subject)
    else:
        print("Subject not found")

    message = re.search(r'\*message:"(.*?)"', text)
    if message:
        message = message.group(1)
        print("Message: ", message)
    else:
        print('"Message" not found')

    email_fields = {
        'from': _from,
        'raw_subject': subject,
        'raw_message': message
    }

    return email_fields


def build_bulk_emails(raw_subject: str, raw_message: str):
    message_df = pd.read_csv('message_vars.csv')
    subject_df = pd.read_csv('subject_vars.csv')
    print(message_df)
    print(subject_df)

    assert message_df['address'].equals(subject_df['address']), \
        '[ERROR] "Address" columns in message_vars and subject_vars should be equal'

    email_df = pd.DataFrame({'address': message_df['address']})
    print(email_df)

    message_headers = message_df.columns.tolist()
    subject_headers = subject_df.columns.tolist()

    email_df['message'] = list(
        map(lambda x: raw_message.format(*[message_df.loc[x, var] for var in message_headers[1:]]),
            email_df.index.tolist()))

    email_df['subject'] = list(
        map(lambda x: raw_subject.format(*[subject_df.loc[x, var] for var in subject_headers[1:]]),
            email_df.index.tolist()))

    return email_df





def main():
    # Load email list and messages


    email_list = ["example1@gmail.com", "example2@gmail.com"]  # Replace with your email list
    subject = "Your Personalized Subject"
    message_template = "Hello, this is your personalized message for {}."

    service = service_gmail()
    sender = "your-email@gmail.com"  # Replace with your Gmail address

    fields = get_email_fields()
    email_df = build_bulk_emails(fields['raw_subject'], fields['raw_message'])

    for index in email_df.index.tolist():
        send_email(
            service,
            sender=fields['from'],
            to=email_df.loc[index, 'address'],
            subject=email_df.loc[index, 'subject'],
            message_text=email_df.loc[index, 'message'])


if __name__ == '__main__':
    main()
