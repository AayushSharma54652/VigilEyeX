from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, EmailField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[Length(max=50)])
    last_name = StringField('Last Name', validators=[Length(max=50)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        """Check if username is already in use."""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        """Check if email is already in use."""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class CameraForm(FlaskForm):
    """Form for adding/editing cameras."""
    name = StringField('Camera Name', validators=[DataRequired()])
    url = StringField('Camera URL', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    submit = SubmitField('Save Camera')

class ProfileForm(FlaskForm):
    """Form for editing user profile."""
    first_name = StringField('First Name', validators=[Length(max=50)])
    last_name = StringField('Last Name', validators=[Length(max=50)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password', validators=[
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Update Profile')