from google.oauth2 import service_account
import googleapiclient.discovery

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
]

SERVICE_ACCOUNT_FILE = 'service_account.json'

CALENDER_ID = '35ljjm2g4sagd3cq32jfsok95k@group.calendar.google.com'


def add_calender():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # create google calendar api service
    service = googleapiclient.discovery.build(
      'calendar', 'v3', credentials=credentials)

    body = {
        "id": CALENDER_ID,
    }

    result = service.calendarList().insert(body=body).execute()
    print(result)


if __name__ == '__main__':
    add_calender()
