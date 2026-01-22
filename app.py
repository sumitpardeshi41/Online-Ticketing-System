from flask import Flask, render_template, redirect, url_for, flash, request, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from datetime import datetime
import csv
import io
from config import Config
from models import db, User, BusRoute, Bus, Booking
from forms import *

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# Decorators for role-based access
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def passenger_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_passenger():
            flash('Access denied. Passenger account required.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== Authentication Routes ====================
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register/passenger', methods=['GET', 'POST'])
def passenger_register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = PassengerRegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data,
            user_type='passenger'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('passenger_register.html', form=form)

@app.route('/register/admin', methods=['GET', 'POST'])
def admin_register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = AdminRegistrationForm()
    if form.validate_on_submit():
        if form.admin_code.data != app.config['ADMIN_CODE']:
            flash('Invalid admin code.', 'error')
            return render_template('admin_register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            user_type='admin'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Admin registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('admin_register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('passenger_dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            
            if user.is_admin():
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('passenger_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

# ==================== Passenger Routes ====================
@app.route('/passenger/dashboard')
@login_required
@passenger_required
def passenger_dashboard():
    recent_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).limit(5).all()
    return render_template('passenger/dashboard.html', bookings=recent_bookings)

@app.route('/passenger/search', methods=['GET', 'POST'])
@login_required
@passenger_required
def search_buses():
    form = SearchBusForm()
    buses = []
    
    if request.method == 'GET' and request.args.get('origin'):
        origin = request.args.get('origin')
        destination = request.args.get('destination')
        journey_date_str = request.args.get('journey_date')
        
        try:
            journey_date = datetime.strptime(journey_date_str, '%Y-%m-%d').date()
        except:
            flash('Invalid date format.', 'error')
            return render_template('passenger/search_buses.html', form=form, buses=[])
        
        routes = BusRoute.query.filter(
            BusRoute.origin.ilike(f'%{origin}%'),
            BusRoute.destination.ilike(f'%{destination}%'),
            BusRoute.is_active == True
        ).all()
        
        route_ids = [route.id for route in routes]
        buses = Bus.query.filter(
            Bus.route_id.in_(route_ids),
            Bus.is_active == True
        ).all()
        
        for bus in buses:
            booked_seats = Booking.query.filter_by(
                bus_id=bus.id,
                journey_date=journey_date,
                status='confirmed'
            ).all()
            
            booked_list = []
            for booking in booked_seats:
                booked_list.extend([int(s.strip()) for s in booking.seat_numbers.split(',')])
            
            bus.available_seats = bus.total_seats - len(booked_list)
            bus.booked_seats = booked_list
            bus.journey_date = journey_date_str
    
    return render_template('passenger/search_buses.html', form=form, buses=buses)

@app.route('/passenger/select-seats/<int:bus_id>/<journey_date>', methods=['GET', 'POST'])
@login_required
@passenger_required
def select_seats(bus_id, journey_date):
    bus = Bus.query.get_or_404(bus_id)
    journey_date_obj = datetime.strptime(journey_date, '%Y-%m-%d').date()
    
    booked_bookings = Booking.query.filter_by(
        bus_id=bus_id,
        journey_date=journey_date_obj,
        status='confirmed'
    ).all()
    
    booked_list = []
    for booking in booked_bookings:
        booked_list.extend([int(s.strip()) for s in booking.seat_numbers.split(',')])
    
    form = BookingForm()
    
    if form.validate_on_submit():
        selected_seats = request.form.getlist('seats')
        
        if not selected_seats:
            flash('Please select at least one seat.', 'error')
            return redirect(url_for('select_seats', bus_id=bus_id, journey_date=journey_date))
        
        booking = Booking(
            user_id=current_user.id,
            bus_id=bus_id,
            journey_date=journey_date_obj,
            seat_numbers=','.join(selected_seats),
            total_fare=bus.route.fare * len(selected_seats),
            passenger_name=form.passenger_name.data,
            passenger_age=form.passenger_age.data,
            passenger_gender=form.passenger_gender.data,
            status='confirmed'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Booking confirmed!', 'success')
        return redirect(url_for('booking_confirmation', booking_id=booking.id))
    
    return render_template('passenger/select_seats.html', 
                         bus=bus, 
                         journey_date=journey_date, 
                         booked_seats=booked_list,
                         form=form,
                         total_seats=range(1, bus.total_seats + 1))

@app.route('/passenger/booking-confirmation/<int:booking_id>')
@login_required
@passenger_required
def booking_confirmation(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()
    return render_template('passenger/booking_confirmation.html', booking=booking)

@app.route('/passenger/my-bookings')
@login_required
@passenger_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    return render_template('passenger/my_bookings.html', bookings=bookings)

@app.route('/passenger/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
@passenger_required
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(id=booking_id, user_id=current_user.id).first_or_404()
    
    if booking.status == 'confirmed':
        booking.status = 'cancelled'
        db.session.commit()
        flash('Booking cancelled successfully.', 'success')
    
    return redirect(url_for('my_bookings'))

# ==================== Admin Routes (Add to app.py after passenger routes) ====================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_routes = BusRoute.query.count()
    total_buses = Bus.query.count()
    total_bookings = Booking.query.filter_by(status='confirmed').count()
    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_routes=total_routes,
                         total_buses=total_buses,
                         total_bookings=total_bookings,
                         recent_bookings=recent_bookings)

@app.route('/admin/routes')
@login_required
@admin_required
def manage_routes():
    routes = BusRoute.query.order_by(BusRoute.route_number).all()
    return render_template('admin/manage_routes.html', routes=routes)

@app.route('/admin/routes/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_route():
    form = BusRouteForm()
    
    if form.validate_on_submit():
        # Check if route number already exists
        existing_route = BusRoute.query.filter_by(route_number=form.route_number.data).first()
        if existing_route:
            flash('Route number already exists.', 'error')
            return render_template('admin/add_route.html', form=form)
        
        route = BusRoute(
            route_number=form.route_number.data,
            origin=form.origin.data,
            destination=form.destination.data,
            distance=form.distance.data,
            duration=form.duration.data,
            fare=form.fare.data,
            is_active=form.is_active.data
        )
        
        db.session.add(route)
        db.session.commit()
        
        flash('Route added successfully!', 'success')
        return redirect(url_for('manage_routes'))
    
    return render_template('admin/add_route.html', form=form)

@app.route('/admin/routes/edit/<int:route_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_route(route_id):
    route = BusRoute.query.get_or_404(route_id)
    form = BusRouteForm(obj=route)
    
    if form.validate_on_submit():
        # Check if route number is being changed and if it conflicts
        if form.route_number.data != route.route_number:
            existing_route = BusRoute.query.filter_by(route_number=form.route_number.data).first()
            if existing_route:
                flash('Route number already exists.', 'error')
                return render_template('admin/edit_route.html', form=form, route=route)
        
        route.route_number = form.route_number.data
        route.origin = form.origin.data
        route.destination = form.destination.data
        route.distance = form.distance.data
        route.duration = form.duration.data
        route.fare = form.fare.data
        route.is_active = form.is_active.data
        
        db.session.commit()
        
        flash('Route updated successfully!', 'success')
        return redirect(url_for('manage_routes'))
    
    return render_template('admin/edit_route.html', form=form, route=route)

@app.route('/admin/routes/delete/<int:route_id>', methods=['POST'])
@login_required
@admin_required
def delete_route(route_id):
    route = BusRoute.query.get_or_404(route_id)
    
    # This will also delete associated buses due to cascade
    db.session.delete(route)
    db.session.commit()
    
    flash('Route deleted successfully!', 'success')
    return redirect(url_for('manage_routes'))

@app.route('/admin/buses')
@login_required
@admin_required
def manage_buses():
    buses = Bus.query.order_by(Bus.bus_number).all()
    return render_template('admin/manage_buses.html', buses=buses)

@app.route('/admin/buses/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_bus():
    form = BusForm()
    
    # Populate route choices
    routes = BusRoute.query.all()
    form.route_id.choices = [(r.id, f"{r.route_number} - {r.origin} → {r.destination}") for r in routes]
    
    if form.validate_on_submit():
        # Check if bus number already exists
        existing_bus = Bus.query.filter_by(bus_number=form.bus_number.data).first()
        if existing_bus:
            flash('Bus number already exists.', 'error')
            return render_template('admin/add_bus.html', form=form)
        
        bus = Bus(
            bus_number=form.bus_number.data,
            bus_type=form.bus_type.data,
            total_seats=form.total_seats.data,
            route_id=form.route_id.data,
            departure_time=form.departure_time.data,
            arrival_time=form.arrival_time.data,
            is_active=form.is_active.data
        )
        
        db.session.add(bus)
        db.session.commit()
        
        flash('Bus added successfully!', 'success')
        return redirect(url_for('manage_buses'))
    
    return render_template('admin/add_bus.html', form=form)

@app.route('/admin/buses/edit/<int:bus_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_bus(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    form = BusForm(obj=bus)
    
    # Populate route choices
    routes = BusRoute.query.all()
    form.route_id.choices = [(r.id, f"{r.route_number} - {r.origin} → {r.destination}") for r in routes]
    
    if form.validate_on_submit():
        # Check if bus number is being changed and if it conflicts
        if form.bus_number.data != bus.bus_number:
            existing_bus = Bus.query.filter_by(bus_number=form.bus_number.data).first()
            if existing_bus:
                flash('Bus number already exists.', 'error')
                return render_template('admin/edit_bus.html', form=form, bus=bus)
        
        bus.bus_number = form.bus_number.data
        bus.bus_type = form.bus_type.data
        bus.total_seats = form.total_seats.data
        bus.route_id = form.route_id.data
        bus.departure_time = form.departure_time.data
        bus.arrival_time = form.arrival_time.data
        bus.is_active = form.is_active.data
        
        db.session.commit()
        
        flash('Bus updated successfully!', 'success')
        return redirect(url_for('manage_buses'))
    
    return render_template('admin/edit_bus.html', form=form, bus=bus)

@app.route('/admin/buses/delete/<int:bus_id>', methods=['POST'])
@login_required
@admin_required
def delete_bus(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    
    db.session.delete(bus)
    db.session.commit()
    
    flash('Bus deleted successfully!', 'success')
    return redirect(url_for('manage_buses'))

@app.route('/admin/export-bookings')
@login_required
@admin_required
def export_bookings():
    bookings = Booking.query.all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Booking ID', 'Passenger', 'Bus', 'Route', 'Date', 'Seats', 'Fare', 'Status', 'Booking Date'])
    
    # Write data
    for booking in bookings:
        writer.writerow([
            booking.id,
            booking.user.username,
            booking.bus.bus_number,
            f"{booking.bus.route.origin} → {booking.bus.route.destination}",
            booking.journey_date.strftime('%Y-%m-%d'),
            booking.seat_numbers,
            f"₹{booking.total_fare}",
            booking.status,
            booking.booking_date.strftime('%Y-%m-%d %H:%M')
        ])
    
    # Prepare response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'bookings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

if __name__ == '__main__':
    app.run(debug=True)