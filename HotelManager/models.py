from datetime import datetime
from app import db

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    
    bookings = db.relationship('Booking', backref='room', lazy=True)
    
    def __repr__(self):
        return f"Room('{self.room_number}', '{self.room_type}', ${self.price_per_night:.2f})"

class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    id_type = db.Column(db.String(50), nullable=True)
    id_number = db.Column(db.String(50), nullable=True)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    bookings = db.relationship('Booking', backref='guest', lazy=True)
    
    def __repr__(self):
        return f"Guest('{self.name}', '{self.email}')"

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in_date = db.Column(db.DateTime, nullable=False)
    check_out_date = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, cancelled, checked-out
    
    def __repr__(self):
        return f"Booking(Guest ID: {self.guest_id}, Room ID: {self.room_id}, Check-in: {self.check_in_date.strftime('%Y-%m-%d')})"
