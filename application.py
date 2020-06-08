import datetime
import copy

import google.oauth2.service_account
import googleapiclient.discovery

import flask
import logging
import iso8601

from SurgeryForm import SurgeryForm

logging.basicConfig(filename='booking.log', level=logging.INFO)

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
        "summary": BOOKED_PREFIX + event['summary'],
        "description": "Name: {}\nEmail: {}\nHow we can help: {}".format(
            name, email, description
        )
    })

    service.events().update(calendarId=calender_id,
                            eventId=event['id'],
                            body=body).execute()


@app.route('/', methods=('GET', 'POST'))
def booking():
    credentials = \
        google.oauth2.service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # create google calendar api service
    service = googleapiclient.discovery.build(
        'calendar', 'v3', credentials=credentials)

    events = []
    num_requests = 0
    while num_requests < 5 and len(events) < 10:
        potential_events = get_upcoming_events(service, CALENDER_ID)
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
                   CALENDER_ID,
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
    app.run(debug=True)
