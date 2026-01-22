from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, BooleanField, DateField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange
from models import User

class PassengerRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class AdminRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    admin_code = StringField('Admin Code', validators=[DataRequired()])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class BusRouteForm(FlaskForm):
    route_number = StringField('Route Number', validators=[DataRequired(), Length(max=10)])
    origin = StringField('Origin City', validators=[DataRequired(), Length(max=100)])
    destination = StringField('Destination City', validators=[DataRequired(), Length(max=100)])
    distance = FloatField('Distance (km)', validators=[DataRequired(), NumberRange(min=0)])
    duration = StringField('Duration (HH:MM:SS)', validators=[DataRequired()])
    fare = FloatField('Fare (₹)', validators=[DataRequired(), NumberRange(min=0)])
    is_active = BooleanField('Active Route')

class BusForm(FlaskForm):
    bus_number = StringField('Bus Number', validators=[DataRequired(), Length(max=20)])
    bus_type = SelectField('Bus Type', choices=[('AC', 'AC'), ('Non-AC', 'Non-AC'), ('Sleeper', 'Sleeper'), ('Semi-Sleeper', 'Semi-Sleeper')], validators=[DataRequired()])
    total_seats = IntegerField('Total Seats', validators=[DataRequired(), NumberRange(min=1, max=60)])
    route_id = SelectField('Route', coerce=int, validators=[DataRequired()])
    departure_time = StringField('Departure Time', validators=[DataRequired()])
    arrival_time = StringField('Arrival Time', validators=[DataRequired()])
    is_active = BooleanField('Active Bus')

class SearchBusForm(FlaskForm):
    origin = StringField('From (Origin)', validators=[DataRequired()])
    destination = StringField('To (Destination)', validators=[DataRequired()])
    journey_date = DateField('Journey Date', validators=[DataRequired()])

class BookingForm(FlaskForm):
    passenger_name = StringField('Passenger Name', validators=[DataRequired(), Length(max=100)])
    passenger_age = IntegerField('Age', validators=[DataRequired(), NumberRange(min=1, max=120)])
    passenger_gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[DataRequired()])