from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, TextField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Email, InputRequired

class SurgeryForm(FlaskForm):
    """Contact form."""
    name = StringField('Name', [
        DataRequired()])
    email = StringField('Email', [
        Email(message=('Not a valid email address.')),
        DataRequired()])
    date = SelectField('Date', validators=[InputRequired()])
    body = TextField('How we can help', [
        DataRequired(),
        Length(min=4, message=('Your message is too short.'))])
    recaptcha = RecaptchaField()
    submit = SubmitField('Submit')
