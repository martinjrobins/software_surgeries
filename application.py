import datetime
import copy

import google.oauth2.service_account
import googleapiclient.discovery

import flask
import logging
import iso8601
import requests
import os

from SurgeryForm import SurgeryForm
from emailInvite import email_invite

logging.basicConfig(filename='booking.log', level=logging.INFO)


GITHUB_AUTH_TOKEN = os.environ.get('GITHUB_AUTH_TOKEN')
GITHUB_API_URL = 'https://api.github.com'
GITHUB_AUTH_HEADER = {
    'Content-Type': 'application/json',
    'Authorization': 'token {}'.format(GITHUB_AUTH_TOKEN)
}
GITHUB_OWNER = 'OxfordRSE'
GITHUB_REPO = 'software-surgeries'


def github_post(payload, url):
    results = requests.post(GITHUB_API_URL + url,
                            json=payload, headers=GITHUB_AUTH_HEADER)
    results.raise_for_status()
    return results.json()


def github_get(payload, url):
    results = requests.get(GITHUB_API_URL + url,
                           json=payload, headers=GITHUB_AUTH_HEADER)
    results.raise_for_status()
    return results.json()


SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly',
]

SERVICE_ACCOUNT_FILE = 'service_account.json'

BOOKED_PREFIX = "BOOKED: "

# 'OxRSE bookings' calendar
CALENDER_ID = '35ljjm2g4sagd3cq32jfsok95k@group.calendar.google.com'

# create web app
app = flask.Flask(__name__, instance_relative_config=False)
app.config.from_pyfile('config.cfg')


def get_google_link(title, start_date, end_date, details):
    """
    start/end_date = YmdTH00
    """
    return ('http: // www.google.com/calendar/render?'
            'action=TEMPLATE'
            '&text={}'
            '&dates={}/{}]'
            '&details={}'
            '&location=telecon'
            '&sf=true&output=xml').format(
        title, start_date, end_date, details
    )


def get_upcoming_events(service, calenderId):
    logging.debug('Get upcoming events')
    # 'Z' indicates UTC time
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId=calenderId, timeMin=now,
                                          maxResults=100, singleEvents=True,
                                          orderBy='startTime').execute()
    return events_result.get('items', [])


def book_event(service, calender_id, event, form):
    logging.debug('Booking event {} {} {}'.format(calender_id, event, form))

    start_date = iso8601.parse_date(event['start']['dateTime'])
    end_date = iso8601.parse_date(event['end']['dateTime'])
    date_readable = \
        '{}: {} - {}'.format(
            start_date.strftime("%A %d. %B %Y"),
            start_date.strftime("%H:%M"),
            end_date.strftime("%H:%M")
        )
    start_date_googleformat = start_date.strftime("%Y%M%DT%H%M00")
    end_date_googleformat = end_date.strftime("%Y%M%DT%H%M00")

    markdown = '''
###### Name
{}
###### Affiliation
{}
###### Contact email address
{}
###### Short description of your software
{}
###### How might we be able to help?
{}
###### Useful information
{}
###### Date
{}
'''.format(
        form.name.data,
        form.affiliation.data,
        form.email.data,
        form.description.data,
        form.how.data,
        form.other.data,
        date_readable,
    )

    body = copy.copy(event)
    body.update({
        "summary": BOOKED_PREFIX + event['summary'],
        "description": markdown
    })

    logging.debug('updating calender with body: {}'.format(body))

    service.events().update(calendarId=calender_id,
                            eventId=event['id'],
                            body=body).execute()
    url = '/repos/{}/{}/issues'.format(GITHUB_OWNER, GITHUB_REPO)
    payload = {
        "title": "{} ({})".format(form.name.data, form.affiliation.data),
        "body": markdown,
        "assignees": [
        ],
    }
    logging.debug('github post to url {} with payload {}'.format(url, payload))
    github_post(payload, url)

    warning = '''
This is an automated email to confirm your software surgery booking

Do not reply to this email, if you want to email the OxRSE group please use
rse@cs.ox.ac.uk

'''

    email_invite(to_email=form.email.data,
                 from_email="oxfordrse@gmail.com",
                 subject="Software surgery for {} ({})".format(
                     form.name.data, form.affiliation.data),
                 location="tbd",
                 description=warning + markdown,
                 start=start_date,
                 end=end_date
                 )


@app.route('/', methods=('GET', 'POST'))
def booking():
    credentials = \
        google.oauth2.service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # create google calendar api service
    service = googleapiclient.discovery.build(
        'calendar', 'v3', credentials=credentials)

    potential_events = get_upcoming_events(service, CALENDER_ID)
    events = [e for e in potential_events
              if not e['summary'].startswith(BOOKED_PREFIX)]
    events = events[: 10]

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
                   CALENDER_ID,
                   event, form)

        return flask.redirect(flask.url_for('success'))

    return flask.render_template('booking.html', form=form)


@app.route('/success', methods=('GET', 'POST'))
def success():
    return flask.render_template('success.html')


if __name__ == '__main__':
    app.run(debug=True)
