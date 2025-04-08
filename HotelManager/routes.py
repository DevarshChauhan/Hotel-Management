from flask import render_template, request, redirect, url_for, flash, jsonify, session
from app import app, db
from models import Room, Guest, Booking
from datetime import datetime
from sqlalchemy import and_, or_

@app.template_filter('format_date')
def format_date_filter(date_obj):
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        except ValueError:
            try:
                date_obj = datetime.strptime(date_obj, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return date_obj
    
    if isinstance(date_obj, datetime):
        # Indian date format: DD-MM-YYYY
        return date_obj.strftime('%d-%m-%Y')
    return str(date_obj)

@app.template_filter('inr_currency')
def inr_currency_filter(value):
    """Convert number to Indian Rupee format (₹)"""
    if isinstance(value, (int, float)):
        # Format for Indian rupees, e.g., ₹1,23,456.78
        value_str = f"{value:.2f}"
        main, *decimal = value_str.split('.')
        
        # Format with Indian thousands separator style (1,23,456)
        result = ""
        for i, char in enumerate(reversed(main)):
            if i == 3:
                result = "," + result
            elif i > 3 and (i - 3) % 2 == 0:
                result = "," + result
            result = char + result
            
        # Add decimal part (if any)
        if decimal:
            result = f"{result}.{decimal[0]}"
            
        # Add Rupee symbol
        return f"₹{result}"
    return value

def calculate_nights(check_in, check_out):
    """Calculate number of nights between two dates"""
    if isinstance(check_in, str):
        check_in = datetime.strptime(check_in, '%Y-%m-%d')
    if isinstance(check_out, str):
        check_out = datetime.strptime(check_out, '%Y-%m-%d')
    
    delta = check_out - check_in
    return delta.days

@app.route('/')
def index():
    # Get summary information for dashboard
    total_rooms = Room.query.count()
    available_rooms = Room.query.filter_by(is_available=True).count()
    total_guests = Guest.query.count()
    active_bookings = Booking.query.filter_by(status='confirmed').count()
    
    # Get latest bookings for dashboard
    latest_bookings = Booking.query.filter_by(status='confirmed').order_by(Booking.booking_date.desc()).limit(5).all()
    
    return render_template(
        'index.html',
        total_rooms=total_rooms,
        available_rooms=available_rooms,
        total_guests=total_guests,
        active_bookings=active_bookings,
        latest_bookings=latest_bookings
    )

# Room routes
@app.route('/rooms')
def rooms():
    rooms_data = Room.query.all()
    return render_template('rooms.html', rooms=rooms_data)

@app.route('/rooms/availability', methods=['GET', 'POST'])
def check_availability():
    if request.method == 'POST':
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        
        if not check_in or not check_out:
            flash('Please select both check-in and check-out dates', 'danger')
            return redirect(url_for('rooms'))
        
        # Validate dates
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
            
            if check_in_date >= check_out_date:
                flash('Check-out date must be after check-in date', 'danger')
                return redirect(url_for('rooms'))
                
            if check_in_date < datetime.today():
                flash('Check-in date cannot be in the past', 'danger')
                return redirect(url_for('rooms'))
        except ValueError:
            flash('Invalid date format', 'danger')
            return redirect(url_for('rooms'))
        
        # Find bookings that overlap with the requested dates
        overlapping_bookings = Booking.query.filter(
            and_(
                Booking.status == 'confirmed',
                or_(
                    and_(Booking.check_in_date <= check_in_date, Booking.check_out_date > check_in_date),
                    and_(Booking.check_in_date < check_out_date, Booking.check_out_date >= check_out_date),
                    and_(Booking.check_in_date >= check_in_date, Booking.check_out_date <= check_out_date)
                )
            )
        ).all()
        
        # Get the room IDs of all booked rooms
        booked_room_ids = [booking.room_id for booking in overlapping_bookings]
        
        # Filter rooms that are not in the booked list
        if booked_room_ids:
            available_rooms = Room.query.filter(~Room.id.in_(booked_room_ids)).all()
        else:
            available_rooms = Room.query.all()
        
        # Calculate nights
        nights = calculate_nights(check_in, check_out)
        
        # Store dates in session for booking
        session['check_in'] = check_in
        session['check_out'] = check_out
        session['nights'] = nights
        
        return render_template(
            'rooms.html', 
            rooms=available_rooms, 
            check_in=check_in,
            check_out=check_out,
            nights=nights,
            is_availability_search=True
        )
    
    return redirect(url_for('rooms'))

# Guest routes
@app.route('/guests')
def guests():
    search_query = request.args.get('search', '')
    
    if search_query:
        guests_data = Guest.query.filter(
            or_(
                Guest.name.ilike(f'%{search_query}%'),
                Guest.email.ilike(f'%{search_query}%'),
                Guest.phone.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        guests_data = Guest.query.all()
        
    return render_template('guests.html', guests=guests_data, search_query=search_query)

@app.route('/guests/add', methods=['GET', 'POST'])
def add_guest():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        id_type = request.form.get('id_type')
        id_number = request.form.get('id_number')
        
        # Basic validation
        if not name or not email or not phone:
            flash('Name, email and phone are required fields', 'danger')
            return render_template('add_guest.html', guest={
                'name': name,
                'email': email,
                'phone': phone,
                'address': address,
                'id_type': id_type,
                'id_number': id_number
            })
        
        # Add guest to database
        new_guest = Guest(
            name=name,
            email=email,
            phone=phone,
            address=address,
            id_type=id_type,
            id_number=id_number
        )
        db.session.add(new_guest)
        db.session.commit()
        
        flash('Guest added successfully', 'success')
        return redirect(url_for('guests'))
    
    return render_template('add_guest.html')

@app.route('/guests/edit/<int:guest_id>', methods=['GET', 'POST'])
def edit_guest(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        id_type = request.form.get('id_type')
        id_number = request.form.get('id_number')
        
        # Basic validation
        if not name or not email or not phone:
            flash('Name, email and phone are required fields', 'danger')
            return render_template('edit_guest.html', guest=guest)
        
        # Update guest in database
        guest.name = name
        guest.email = email
        guest.phone = phone
        guest.address = address
        guest.id_type = id_type
        guest.id_number = id_number
        
        db.session.commit()
        flash('Guest updated successfully', 'success')
        return redirect(url_for('guests'))
    
    return render_template('edit_guest.html', guest=guest)

@app.route('/guests/delete/<int:guest_id>', methods=['POST'])
def delete_guest(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    
    # Check if guest has bookings
    bookings = Booking.query.filter_by(guest_id=guest_id).all()
    
    if bookings:
        flash('Cannot delete guest with bookings', 'danger')
    else:
        db.session.delete(guest)
        db.session.commit()
        flash('Guest deleted successfully', 'success')
    
    return redirect(url_for('guests'))

# Booking routes
@app.route('/bookings')
def bookings():
    bookings_data = Booking.query.all()
    
    for booking in bookings_data:
        # Calculate nights
        booking.nights = calculate_nights(booking.check_in_date, booking.check_out_date)
    
    return render_template('bookings.html', bookings=bookings_data)

@app.route('/bookings/add', methods=['GET', 'POST'])
def add_booking():
    rooms = Room.query.all()
    guests = Guest.query.all()
    
    if request.method == 'POST':
        try:
            room_id = int(request.form.get('room_id'))
            guest_id = int(request.form.get('guest_id'))
            check_in = request.form.get('check_in')
            check_out = request.form.get('check_out')
            
            # Validate input
            if not room_id or not guest_id or not check_in or not check_out:
                flash('All fields are required', 'danger')
                return render_template('add_booking.html', rooms=rooms, guests=guests)
            
            # Validate dates
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
            
            if check_in_date >= check_out_date:
                flash('Check-out date must be after check-in date', 'danger')
                return render_template('add_booking.html', rooms=rooms, guests=guests)
                
            if check_in_date < datetime.today():
                flash('Check-in date cannot be in the past', 'danger')
                return render_template('add_booking.html', rooms=rooms, guests=guests)
            
            # Check if room exists
            room = Room.query.get(room_id)
            if not room:
                flash('Room not found', 'danger')
                return render_template('add_booking.html', rooms=rooms, guests=guests)
            
            # Check if guest exists
            guest = Guest.query.get(guest_id)
            if not guest:
                flash('Guest not found', 'danger')
                return render_template('add_booking.html', rooms=rooms, guests=guests)
            
            # Check if room is available for those dates
            overlapping_bookings = Booking.query.filter(
                and_(
                    Booking.room_id == room_id,
                    Booking.status == 'confirmed',
                    or_(
                        and_(Booking.check_in_date <= check_in_date, Booking.check_out_date > check_in_date),
                        and_(Booking.check_in_date < check_out_date, Booking.check_out_date >= check_out_date),
                        and_(Booking.check_in_date >= check_in_date, Booking.check_out_date <= check_out_date)
                    )
                )
            ).all()
            
            if overlapping_bookings:
                flash('Room is not available for the selected dates', 'danger')
                return render_template('add_booking.html', rooms=rooms, guests=guests)
            
            # Calculate total price
            nights = calculate_nights(check_in, check_out)
            total_price = room.price_per_night * nights
            
            # Create booking
            new_booking = Booking(
                guest_id=guest_id,
                room_id=room_id,
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                total_price=total_price,
                status='confirmed'
            )
            
            db.session.add(new_booking)
            db.session.commit()
            
            flash('Booking added successfully', 'success')
            return redirect(url_for('bookings'))
            
        except ValueError as e:
            flash(f'Invalid data format: {str(e)}', 'danger')
            return render_template('add_booking.html', rooms=rooms, guests=guests)
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return render_template('add_booking.html', rooms=rooms, guests=guests)
    
    return render_template('add_booking.html', rooms=rooms, guests=guests)

@app.route('/bookings/edit/<int:booking_id>', methods=['GET', 'POST'])
def edit_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    rooms = Room.query.all()
    guests = Guest.query.all()
    
    if request.method == 'POST':
        try:
            room_id = int(request.form.get('room_id'))
            guest_id = int(request.form.get('guest_id'))
            check_in = request.form.get('check_in')
            check_out = request.form.get('check_out')
            status = request.form.get('status')
            
            # Validate input
            if not room_id or not guest_id or not check_in or not check_out or not status:
                flash('All fields are required', 'danger')
                return render_template('edit_booking.html', booking=booking, rooms=rooms, guests=guests)
            
            # Validate dates
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
            
            if check_in_date >= check_out_date:
                flash('Check-out date must be after check-in date', 'danger')
                return render_template('edit_booking.html', booking=booking, rooms=rooms, guests=guests)
            
            # Check if room is available for those dates (if room is changing)
            if room_id != booking.room_id:
                overlapping_bookings = Booking.query.filter(
                    and_(
                        Booking.room_id == room_id,
                        Booking.id != booking_id,
                        Booking.status == 'confirmed',
                        or_(
                            and_(Booking.check_in_date <= check_in_date, Booking.check_out_date > check_in_date),
                            and_(Booking.check_in_date < check_out_date, Booking.check_out_date >= check_out_date),
                            and_(Booking.check_in_date >= check_in_date, Booking.check_out_date <= check_out_date)
                        )
                    )
                ).all()
                
                if overlapping_bookings:
                    flash('Room is not available for the selected dates', 'danger')
                    return render_template('edit_booking.html', booking=booking, rooms=rooms, guests=guests)
            
            # Calculate total price
            room = Room.query.get(room_id)
            nights = calculate_nights(check_in, check_out)
            total_price = room.price_per_night * nights
            
            # Update booking
            booking.guest_id = guest_id
            booking.room_id = room_id
            booking.check_in_date = check_in_date
            booking.check_out_date = check_out_date
            booking.total_price = total_price
            booking.status = status
            
            db.session.commit()
            
            flash('Booking updated successfully', 'success')
            return redirect(url_for('bookings'))
            
        except ValueError as e:
            flash(f'Invalid data format: {str(e)}', 'danger')
            return render_template('edit_booking.html', booking=booking, rooms=rooms, guests=guests)
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return render_template('edit_booking.html', booking=booking, rooms=rooms, guests=guests)
    
    return render_template('edit_booking.html', booking=booking, rooms=rooms, guests=guests)

@app.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    booking.status = 'cancelled'
    db.session.commit()
    
    flash('Booking cancelled successfully', 'success')
    return redirect(url_for('bookings'))

@app.route('/api/room/price', methods=['GET'])
def get_room_price():
    room_id = request.args.get('room_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    if not room_id or not check_in or not check_out:
        return jsonify({'error': 'Missing parameters'}), 400
    
    try:
        room_id = int(room_id)
        room = Room.query.get(room_id)
        
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        nights = calculate_nights(check_in, check_out)
        price_per_night = room.price_per_night
        total_price = price_per_night * nights
        
        return jsonify({
            'price_per_night': price_per_night,
            'nights': nights,
            'total_price': total_price
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
