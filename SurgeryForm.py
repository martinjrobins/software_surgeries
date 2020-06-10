from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, TextField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, InputRequired, Optional


class SurgeryForm(FlaskForm):
    name = StringField('Name', [DataRequired()])

    affiliation = StringField(
        'Affiliation (Please specify department and research group)',
        [DataRequired()],
        description='Please specify department and research group.'
    )
    email = StringField('Email address', [
        Email(message=('Not a valid email address.')),
        DataRequired()])
    description = TextAreaField('Short description of your software', [
        DataRequired()])

    how = TextAreaField('How might we be able to help?', [DataRequired()])
    other = TextAreaField(
        'If there is anything we might find useful to see'
        ' before we meet, such as links to software (if public),'
        ' user guides etc, please provide links here',
        [Optional()]
    )

    date = SelectField('Date (click to choose from available dates)',
                       validators=[InputRequired()],
                       description='click to choose from available dates')
    where = StringField('Where did you hear about the Software Surgeries?',
                        [Optional()])
    submit = SubmitField('Submit')
