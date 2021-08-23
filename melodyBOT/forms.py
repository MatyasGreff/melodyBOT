#importing modules
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from melodyBOT.models import User


#forms with validators
class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=2, max=20)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):

        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken, Please choose a different one.')
        invalid_chars = " :;-/*~'!"
        for char in username.data:
            if char in invalid_chars:
                raise ValidationError('That username contains invalid characters. Make sure the username only contains letters and numeric characters.')
    def validate_email(self, email):

        email = User.query.filter_by(email=email.data).first()
        if email:
            raise ValidationError('That email is taken, Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

#melody generation form
class GenerationForm(FlaskForm):
    model = SelectField('Model',
                        choices=[('basic_rnn', 'Basic'), ('lookback_rnn', 'Lookback'), ('attention_rnn', 'Attention')])
    num_steps = SelectField('Length',
                        choices=[('100', 'Short'), ('200', 'Normal'), ('300', 'Long'), ('400', 'Very Long')])
    primer_melody = FileField('Upload primer melody', validators=[FileAllowed(['mid'])])
    submit = SubmitField('Generate!')




class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])

    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken, Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            email = User.query.filter_by(email=email.data).first()
            if email:
                raise ValidationError('That email is taken, Please choose a different one.')


class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):

        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. Register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class MIDIPlayer(FlaskForm):
    melody = FileField('Play any single channel MIDI from your hard-drive', validators=[FileAllowed(['mid'])])
    submit = SubmitField('Load MIDI!')
