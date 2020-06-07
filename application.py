import datetime
from googleapiclient.discovery import build
from flask import Flask, url_for, render_template, redirect
from utils import get_api_credentials, get_calender, book_event
from SurgeryForm import SurgeryForm
import iso8601


# If modifying these scopes, delete the file token.pickle.
CALENDER_NAME = 'OxRSE bookings'

# create web app
app = Flask(__name__, instance_relative_config=False)
app.config.from_pyfile('config.cfg')

# create google calendar api service
service = build('calendar', 'v3', credentials=get_api_credentials())


@app.route('/', methods=('GET', 'POST'))
def contact():
    calender = get_calender(service, CALENDER_NAME)
    events = get_upcoming_events(calender['id'])

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

        return redirect(url_for('success'))

    return render_template('booking.html', form=form)


@app.route('/success', methods=('GET', 'POST'))
def success():
    return render_template('success.html')


if __name__ == '__main__':
    app.run(debug=True)
