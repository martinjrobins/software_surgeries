
import datetime
from emailInvite import email_invite

email_invite(to_email='martinjrobins@gmail.com',
             from_email="oxfordrse@gmail.com",
             subject="my test",
             location="tbd",
             description="test description",
             start=datetime.datetime.now(),
             end=datetime.datetime.now() + datetime.timedelta(hours=9),
             )
