from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
import smtplib
import datetime as dt
import icalendar
import logging
import uuid
from mailjet_rest import Client
import os

MAIL_USER = 'ce9728ec796be11ea918e9dfd32652d5'
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_SERVER = 'in-v3.mailjet.com'

def email_invite(to_email, from_email, subject, location, description, start, end):
    logging.debug('send email with params {}'.format({
        "to_email": to_email,
        "from_email": from_email,
        "subject": subject,
        "location": location,
        "description": description,
        "start": start,
        "end": end,
    }))
    # Timezone to use for our dates - change as needed
    cal = icalendar.Calendar()
    cal.add('prodid', '-//My calendar application//example.com//')
    cal.add('version', '2.0')
    cal.add('method', "REQUEST")
    event = icalendar.Event()
    event.add('attendee', to_email)
    event.add('attendee', to_email)
    event.add('organizer', from_email)
    event.add('status', "confirmed")
    event.add('category', "Event")
    event.add('summary', subject)
    event.add('description', description)
    event.add('location', "tbd")
    event.add('dtstart', start)
    event.add('dtend', end)
    event.add('dtstamp', dt.datetime.now())
    event['uid'] = uuid.uuid1()  # Generate some unique ID
    event.add('priority', 5)
    event.add('sequence', 1)
    event.add('created', dt.datetime.now())

    cal.add_component(event)

    msg = MIMEMultipart("alternative")

    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Content-class"] = "urn:content-classes:calendarmessage"

    msg.attach(MIMEText(description))

    filename = "invite.ics"
    part = MIMEBase('text', "calendar", method="REQUEST", name=filename)
    part.set_payload(cal.to_ical())
    encoders.encode_base64(part)
    part.add_header('Content-Description', filename)
    part.add_header("Content-class", "urn:content-classes:calendarmessage")
    part.add_header("Filename", filename)
    part.add_header("Path", filename)
    msg.attach(part)

    server = smtplib.SMTP(MAIL_SERVER, 25)
    server.starttls()
    server.ehlo()
    server.login(MAIL_USER, MAIL_PASSWORD)
    server.sendmail(msg["From"], [msg["To"]], msg.as_string())
    server.quit()
