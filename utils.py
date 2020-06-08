import os.path
import datetime
import pickle
import logging
import copy
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

logging.basicConfig(filename='booking.log', level=logging.DEBUG)

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly',
]


def get_api_credentials():
    logging.debug('Get api credentials')

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        logging.debug('Authorization: token.pickle already exists')
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.debug('Authorization: refreshing token')
            creds.refresh(Request())
        else:
            logging.debug('Authorization: user authentication required')
            flow = Flow.from_client_secrets_file(
                'credentials.json',
                scopes=SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            # Tell the user to go to the authorization URL.
            auth_url, _ = flow.authorization_url(prompt='consent')

            print('Please go to this URL: {}'.format(auth_url))

            # The user will get an authorization code. This code is used to get the
            # access token.
            code = input('Enter the authorization code: ')
            flow.fetch_token(code=code)

            # You can use flow.credentials, or you can just get a requests session
            # using flow.authorized_session.
            session = flow.authorized_session()
            print(session.get('https://www.googleapis.com/userinfo/v2/me').json())

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

def get_calender(service, name):
    logging.debug('Getting calender {}'.format(name))
    calender_list_result = service.calendarList().list().execute()
    calender_list = calender_list_result.get('items', [])
    calender = [c for c in calender_list if c['summary'] == name]
    if len(calender) != 1:
        raise RuntimeError('Found {} calenders matching {}'.format(
            len(calender), name
        ))
    return calender[0]

def get_upcoming_events(service, calenderId):
    logging.debug('Get upcoming events')
    # 'Z' indicates UTC time
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId=calenderId, timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    return events_result.get('items', [])


def book_event(service, calender_id, event, name, email, description):
    logging.debug('Booking event {} {}: {}, {}, {}'.format(
        event['id'], event['summary'], name, email, description))

    body = copy.copy(event)
    body.update({
        "attendees":
        [{
            "displayName": name,
            "email": email,
            "responseStatus": "accepted",
        }],
        "summary": "BOOKED: " + event['summary'],
        "description": description,
    })

    service.events().update(calendarId=calender_id,
                            eventId=event['id'],
                            body=body).execute()

