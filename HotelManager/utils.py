import os
import json
from datetime import datetime
from flask import flash

# Define file paths
ROOMS_FILE = 'data/rooms.json'
GUESTS_FILE = 'data/guests.json'
BOOKINGS_FILE = 'data/bookings.json'

def initialize_data_files():
    """Initialize empty JSON files if they don't exist"""
    files = [ROOMS_FILE, GUESTS_FILE, BOOKINGS_FILE]
    
    for file_path in files:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                if file_path == ROOMS_FILE:
                    # Initialize with some default rooms
                    rooms = [
                        {
                            "id": 1,
                            "room_number": "101",
                            "room_type": "Standard",
                            "price_per_night": 500,
                            "is_available": True
                        },
                        {
                            "id": 2,
                            "room_number": "102",
                            "room_type": "Standard",
                            "price_per_night": 500,
                            "is_available": True
                        },
                        {
                            "id": 3,
                            "room_number": "201",
                            "room_type": "Deluxe",
                            "price_per_night": 1200,
                            "is_available": True
                        },
                        {
                            "id": 4,
                            "room_number": "301",
                            "room_type": "Suite",
                            "price_per_night": 1800,
                            "is_available": True
                        }
                    ]
                    json.dump(rooms, f, indent=4)
                else:
                    json.dump([], f, indent=4)

def load_data(file_path):
    """Load data from JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is empty/invalid, return empty list
        return []

def save_data(file_path, data):
    """Save data to JSON file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Room operations
def get_all_rooms():
    """Get all rooms"""
    return load_data(ROOMS_FILE)

def get_room_by_id(room_id):
    """Get room by ID"""
    rooms = get_all_rooms()
    for room in rooms:
        if room['id'] == room_id:
            return room
    return None

def update_room_availability(room_id, is_available):
    """Update room availability"""
    rooms = get_all_rooms()
    for room in rooms:
        if room['id'] == room_id:
            room['is_available'] = is_available
            save_data(ROOMS_FILE, rooms)
            return True
    return False

# Guest operations
def get_all_guests():
    """Get all guests"""
    return load_data(GUESTS_FILE)

def get_guest_by_id(guest_id):
    """Get guest by ID"""
    guests = get_all_guests()
    for guest in guests:
        if guest['id'] == guest_id:
            return guest
    return None

def add_guest(guest_data):
    """Add a new guest"""
    guests = get_all_guests()
    
    # Generate new ID
    new_id = 1
    if guests:
        new_id = max(guest['id'] for guest in guests) + 1
    
    guest_data['id'] = new_id
    guest_data['registration_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    guests.append(guest_data)
    save_data(GUESTS_FILE, guests)
    
    return new_id

def update_guest(guest_id, guest_data):
    """Update a guest's information"""
    guests = get_all_guests()
    
    for i, guest in enumerate(guests):
        if guest['id'] == guest_id:
            # Preserve the ID and registration date
            guest_data['id'] = guest_id
            guest_data['registration_date'] = guest.get('registration_date')
            
            guests[i] = guest_data
            save_data(GUESTS_FILE, guests)
            return True
    
    return False

def delete_guest(guest_id):
    """Delete a guest"""
    guests = get_all_guests()
    bookings = get_all_bookings()
    
    # Check if guest has active bookings
    for booking in bookings:
        if booking['guest_id'] == guest_id and booking['status'] == 'confirmed':
            return False, "Cannot delete guest with active bookings"
    
    # Remove guest
    updated_guests = [guest for guest in guests if guest['id'] != guest_id]
    
    if len(updated_guests) == len(guests):
        return False, "Guest not found"
    
    save_data(GUESTS_FILE, updated_guests)
    return True, "Guest deleted successfully"

def search_guests(query):
    """Search for guests by name, email, or phone"""
    guests = get_all_guests()
    results = []
    
    query = query.lower()
    for guest in guests:
        if (query in guest['name'].lower() or 
            query in guest['email'].lower() or 
            query in guest['phone']):
            results.append(guest)
    
    return results

# Booking operations
def get_all_bookings():
    """Get all bookings"""
    return load_data(BOOKINGS_FILE)

def get_booking_by_id(booking_id):
    """Get booking by ID"""
    bookings = get_all_bookings()
    for booking in bookings:
        if booking['id'] == booking_id:
            return booking
    return None

def add_booking(booking_data):
    """Add a new booking"""
    bookings = get_all_bookings()
    
    # Generate new ID
    new_id = 1
    if bookings:
        new_id = max(booking['id'] for booking in bookings) + 1
    
    booking_data['id'] = new_id
    booking_data['booking_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    booking_data['status'] = 'confirmed'
    
    # Update room availability
    update_room_availability(booking_data['room_id'], False)
    
    bookings.append(booking_data)
    save_data(BOOKINGS_FILE, bookings)
    
    return new_id

def update_booking(booking_id, booking_data):
    """Update a booking"""
    bookings = get_all_bookings()
    
    for i, booking in enumerate(bookings):
        if booking['id'] == booking_id:
            # If room is changing, update availability for both rooms
            if booking['room_id'] != booking_data['room_id']:
                # Make the old room available
                update_room_availability(booking['room_id'], True)
                # Make the new room unavailable
                update_room_availability(booking_data['room_id'], False)
            
            # Preserve the ID and booking date
            booking_data['id'] = booking_id
            booking_data['booking_date'] = booking.get('booking_date')
            
            bookings[i] = booking_data
            save_data(BOOKINGS_FILE, bookings)
            return True
    
    return False

def cancel_booking(booking_id):
    """Cancel a booking"""
    bookings = get_all_bookings()
    
    for i, booking in enumerate(bookings):
        if booking['id'] == booking_id and booking['status'] == 'confirmed':
            bookings[i]['status'] = 'cancelled'
            
            # Make the room available again
            update_room_availability(booking['room_id'], True)
            
            save_data(BOOKINGS_FILE, bookings)
            return True
    
    return False

def get_available_rooms(check_in, check_out):
    """Get available rooms for the given date range"""
    rooms = get_all_rooms()
    bookings = get_all_bookings()
    
    # Convert string dates to datetime objects
    check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
    
    # Get IDs of rooms that are booked during the requested period
    booked_room_ids = []
    for booking in bookings:
        if booking['status'] == 'cancelled':
            continue
            
        booking_check_in = datetime.strptime(booking['check_in_date'], '%Y-%m-%d')
        booking_check_out = datetime.strptime(booking['check_out_date'], '%Y-%m-%d')
        
        # Check if there's an overlap in dates
        if (check_in_date <= booking_check_out and check_out_date >= booking_check_in):
            booked_room_ids.append(booking['room_id'])
    
    # Filter available rooms
    available_rooms = [room for room in rooms if room['id'] not in booked_room_ids and room['is_available']]
    
    return available_rooms

def is_room_available(room_id, check_in, check_out):
    """Check if a specific room is available for the given date range"""
    bookings = get_all_bookings()
    
    # Convert string dates to datetime objects
    check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
    
    for booking in bookings:
        if booking['room_id'] == room_id and booking['status'] == 'confirmed':
            booking_check_in = datetime.strptime(booking['check_in_date'], '%Y-%m-%d')
            booking_check_out = datetime.strptime(booking['check_out_date'], '%Y-%m-%d')
            
            # Check if there's an overlap in dates
            if (check_in_date <= booking_check_out and check_out_date >= booking_check_in):
                return False
    
    # Also check if the room is marked as available in general
    room = get_room_by_id(room_id)
    if not room or not room['is_available']:
        return False
    
    return True

def format_date(date_str):
    """Format date string for Indian display format (DD-MM-YYYY)"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d-%m-%Y')
    except:
        return date_str

def calculate_nights(check_in, check_out):
    """Calculate number of nights between two dates"""
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d')
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d')
        delta = check_out_date - check_in_date
        return delta.days
    except:
        return 0

def calculate_total_price(room_id, check_in, check_out):
    """Calculate total price for a booking"""
    room = get_room_by_id(room_id)
    if not room:
        return 0
    
    nights = calculate_nights(check_in, check_out)
    return room['price_per_night'] * nights
