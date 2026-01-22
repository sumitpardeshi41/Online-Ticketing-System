from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(15))
    user_type = db.Column(db.String(10), nullable=False, default='passenger')  # 'passenger' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.user_type == 'admin'
    
    def is_passenger(self):
        return self.user_type == 'passenger'

class BusRoute(db.Model):
    __tablename__ = 'bus_routes'
    
    id = db.Column(db.Integer, primary_key=True)
    route_number = db.Column(db.String(10), unique=True, nullable=False)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    distance = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(20), nullable=False)  # e.g., "5:30:00"
    fare = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    buses = db.relationship('Bus', backref='route', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<BusRoute {self.route_number}: {self.origin} → {self.destination}>"

class Bus(db.Model):
    __tablename__ = 'buses'
    
    id = db.Column(db.Integer, primary_key=True)
    bus_number = db.Column(db.String(20), unique=True, nullable=False)
    bus_type = db.Column(db.String(20), nullable=False)  # 'AC', 'Non-AC', 'Sleeper', 'Semi-Sleeper'
    total_seats = db.Column(db.Integer, nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey('bus_routes.id'), nullable=False)
    departure_time = db.Column(db.String(10), nullable=False)  # e.g., "08:00"
    arrival_time = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    bookings = db.relationship('Booking', backref='bus', lazy=True)
    
    def __repr__(self):
        return f"<Bus {self.bus_number}>"

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bus_id = db.Column(db.Integer, db.ForeignKey('buses.id'), nullable=False)
    journey_date = db.Column(db.Date, nullable=False)
    seat_numbers = db.Column(db.String(200), nullable=False)
    total_fare = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(10), default='confirmed')  # 'confirmed', 'cancelled'
    passenger_name = db.Column(db.String(100), nullable=False)
    passenger_age = db.Column(db.Integer, nullable=False)
    passenger_gender = db.Column(db.String(10), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Booking {self.id}>"