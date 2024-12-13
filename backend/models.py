from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import uuid

db = SQLAlchemy()

def generate_booking_id():
    return str(uuid.uuid4())

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(50), unique=True, nullable=False, default=generate_booking_id)
    email = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False)
    nationality = db.Column(db.String(50), nullable=False)
    adults = db.Column(db.Integer, nullable=False)
    children = db.Column(db.Integer, nullable=False)
    ticket_type = db.Column(db.String(50), nullable=False)
    time_slot = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default='pending')
    
    payment = db.relationship('Payment', backref='booking', lazy=True, uselist=False)

    def to_dict(self):
        try:
            return {
                'id': self.booking_id,
                'email': self.email,
                'date': self.date.strftime('%Y-%m-%d') if self.date else None,
                'nationality': self.nationality,
                'adults': self.adults,
                'children': self.children,
                'ticket_type': self.ticket_type,
                'time_slot': self.time_slot,
                'status': self.status,
                'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
                'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
                'total_amount': float(self.total_amount) if self.total_amount else 0.0,
                'payment_status': self.payment_status,
                'payment': self.payment.to_dict() if self.payment else None
            }
        except Exception as e:
            print(f"Error in Booking.to_dict: {str(e)}")
            return {
                'id': self.booking_id,
                'error': 'Error converting booking to dictionary'
            }

class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    slot_time = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    booked_count = db.Column(db.Integer, default=0)
    ticket_type = db.Column(db.String(50), nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('date', 'slot_time', 'ticket_type', name='unique_timeslot'),
    )
    def has_availability(self, requested_count):
        """Check if the time slot has enough capacity for requested visitors."""
        return (self.capacity - self.booked_count) >= requested_count

    def update_booking_count(self, count):
        """Update the booked count for this time slot."""
        self.booked_count += count
        db.session.commit()

class Pricing(db.Model):
    __tablename__ = 'pricing'
    
    id = db.Column(db.Integer, primary_key=True)
    nationality = db.Column(db.String(50), nullable=False)
    ticket_type = db.Column(db.String(50), nullable=False)
    adult_price = db.Column(db.Float, nullable=False)
    child_price = db.Column(db.Float, nullable=False)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('nationality', 'ticket_type', 'effective_from', name='unique_pricing'),
    )

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(50), db.ForeignKey('bookings.booking_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'amount': self.amount,
            'status': self.status,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
