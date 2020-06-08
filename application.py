import datetime
import os

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

import requests
import copy

import flask
import logging
import iso8601

from SurgeryForm import SurgeryForm

logging.basicConfig(filename='booking.log', level=logging.INFO)

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly',
]

BOOKED_PREFIX = "BOOKED: "


# If modifying these scopes, delete the file token.pickle.
CALENDER_NAME = 'OxRSE bookings'

CLIENT_SECRETS_FILE = "credentials.json"

# create web app
app = flask.Flask(__name__, instance_relative_config=False)
app.config.from_pyfile('config.cfg')


@app.route('/authorize')
def authorize():

    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow
    # steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect
    # URIs for the OAuth 2.0 client, which you configured in the API Console.
    # If this value doesn't match an authorized URI, you will get a
    # 'redirect_uri_mismatch' error.
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server
        # apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true'
    )

    # Store the state so the callback can verify the auth server response.
    flask.session['state'] = state

    return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can
    # verified in the authorization server response.
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session.
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.
    credentials = flow.credentials
    flask.session['credentials'] = credentials_to_dict(credentials)

    return flask.redirect('/')


@app.route('/revoke')
def revoke():
  if 'credentials' not in flask.session:
    return ('You need to <a href="/authorize">authorize</a> before ' +
            'testing the code to revoke credentials.')

  credentials = google.oauth2.credentials.Credentials(
    **flask.session['credentials'])

  revoke = requests.post('https://oauth2.googleapis.com/revoke',
      params={'token': credentials.token},
      headers = {'content-type': 'application/x-www-form-urlencoded'})

  status_code = getattr(revoke, 'status_code')
  if status_code == 200:
    return('Credentials successfully revoked.')
  else:
    return('An error occurred.')


@app.route('/clear')
def clear_credentials():
  if 'credentials' in flask.session:
    del flask.session['credentials']
  return ('Credentials have been cleared.')


def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}

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
        }],
        "summary": BOOKED_PREFIX + event['summary'],
        "description": description,
    })

    service.events().update(calendarId=calender_id,
                            eventId=event['id'],
                            body=body).execute()


@app.route('/', methods=('GET', 'POST'))
def booking():

    if 'credentials' not in flask.session:
        return flask.redirect('authorize')

    # Load credentials from the session.
    credentials = google.oauth2.credentials.Credentials(
      **flask.session['credentials'])

    # create google calendar api service
    service = googleapiclient.discovery.build(
      'calendar', 'v3', credentials=credentials)

    calender = get_calender(service, CALENDER_NAME)
    events = []
    num_requests = 0
    while num_requests < 5 and len(events) < 10:
        potential_events = get_upcoming_events(service, calender['id'])
        num_requests += 1
        events += [e for e in potential_events
                   if not e['summary'].startswith(BOOKED_PREFIX)]

    form = SurgeryForm()
    choices = []
    for e in events:
        start_date = iso8601.parse_date(e['start']['dateTime'])
        end_date = iso8601.parse_date(e['end']['dateTime'])
        choices.append((
            e['id'],
            '{}: {} - {}'.format(
            start_date.strftime("%A %d. %B %Y"),
            start_date.strftime("%H:%M"),
            end_date.strftime("%H:%M")
            )))
    form.date.choices = choices

    if form.validate_on_submit():
        event = [e for e in events if e['id'] == form.date.data][0]
        book_event(service,
                   calender['id'],
                   event,
                   form.name.data,
                   form.email.data,
                   form.body.data)

        return flask.redirect(flask.url_for('success'))

    return flask.render_template('booking.html', form=form)


@app.route('/success', methods=('GET', 'POST'))
def success():
    return flask.render_template('success.html')


if __name__ == '__main__':
    # When running locally, disable OAuthlib's HTTPs verification.
    # ACTION ITEM for developers:
    #     When running in production *do not* leave this option enabled.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Specify a hostname and port that are set as a valid redirect URI
    # for your API project in the Google API Console.
    app.run(debug=True)
