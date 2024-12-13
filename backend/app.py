from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime, timedelta
import os
from models import db, Booking, TimeSlot, Pricing, Payment
from dotenv import load_dotenv
import traceback
from flask_mail import Mail, Message
import uuid
import logging
from werkzeug.serving import WSGIRequestHandler

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('werkzeug')
logger.setLevel(logging.INFO)

# Custom log handler to prevent formatting errors
class SafeLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            print(msg)
        except Exception:
            pass

# Create and add the safe log handler
safe_handler = SafeLogHandler()
logger.addHandler(safe_handler)
logger.propagate = False

# Disable Werkzeug's default logging
import logging
logging.getLogger('werkzeug').disabled = True

# Custom log method for WSGIRequestHandler
def safe_log_request(self, format, *args):
    try:
        if format == 'info':
            # Special case for request logging
            msg, code, size = args
            print(f'Request: {msg}, Status: {code}, Size: {size}')
        else:
            print(format % args if args else format)
    except Exception:
        pass

# Patch WSGIRequestHandler
from werkzeug.serving import WSGIRequestHandler
WSGIRequestHandler.log = safe_log_request

# Load environment variables
load_dotenv()

# Get absolute paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')
DB_PATH = os.path.join(INSTANCE_PATH, 'chatbot.db')

print("=== Server Starting ===")
print(f"Base Directory: {BASE_DIR}")
print(f"Instance Path: {INSTANCE_PATH}")
print(f"Database Path: {DB_PATH}")

app = Flask(__name__, 
           static_folder='../frontend/static',
           static_url_path='/static',
           instance_path=INSTANCE_PATH)

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True
    }
})

# Configure Flask-SQLAlchemy with absolute path
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)
mail = Mail(app)

@app.before_request
def log_request_info():
    logger.info('Headers: %s', dict(request.headers))
    logger.info('Body: %s', request.get_data())

@app.route('/api/bookings/create', methods=['POST'])
def create_booking():
    logger.info('=== Starting Booking Creation ===')
    
    try:
        # Get and log the raw data first
        raw_data = request.get_data()
        logger.info('Raw request data: %s', raw_data)
        
        # Try to parse JSON
        data = request.get_json()
        logger.info('Parsed JSON data: %s', data)
        
        if not data:
            logger.error('No data provided in request')
            return jsonify({'error': 'No data provided'}), 400
            
        # Log the children value specifically
        children_value = data.get('children')
        logger.info('Children value: %s (type: %s)', children_value, type(children_value))
        
        # Validate input data
        required_fields = ['date', 'nationality', 'adults', 'ticketType', 'timeSlot', 'email']
        missing_fields = []

        for field in required_fields:
            if field not in data or data[field] is None or data[field] == '':
                missing_fields.append(field)
                logger.warning('Missing required field: %s', field)
        
        if missing_fields:
            error_msg = f'Missing or empty required fields: {", ".join(missing_fields)}'
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 400
        
        # Process children field
        try:
            children = int(data.get('children', 0))
            data['children'] = children  # Update with processed value
            logger.info('Processed children value: %d', children)
        except (TypeError, ValueError) as e:
            logger.error('Error processing children value: %s', str(e))
            return jsonify({'error': 'Invalid children value'}), 400

        # Validate visitor numbers
        try:
            adults = int(data['adults'])
            if adults < 0:
                return jsonify({'error': 'Number of adults cannot be negative'}), 400
            if children < 0:
                return jsonify({'error': 'Number of children cannot be negative'}), 400
            
            total_visitors = adults + children
            if total_visitors <= 0:
                return jsonify({'error': 'Total number of visitors must be greater than 0'}), 400

            logger.info('Validated visitors - Adults: %d, Children: %d, Total: %d', 
                       adults, children, total_visitors)
        except ValueError:
            return jsonify({'error': 'Invalid visitor numbers'}), 400

        try:
            booking_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            
        # Get pricing information
        try:
            pricing = Pricing.query.filter_by(
                nationality=data['nationality'],
                ticket_type=data['ticketType']
            ).filter(
                Pricing.effective_from <= booking_date,
                Pricing.effective_to >= booking_date
            ).first()
            
            if not pricing:
                return jsonify({'error': 'No valid pricing found for the selected options'}), 400
                
            # Calculate total amount
            total_amount = (adults * pricing.adult_price) + (children * pricing.child_price)
            logger.info('Calculated total amount: %f', total_amount)
            
        except Exception as e:
            logger.error('Error querying pricing: %s', str(e))
            return jsonify({'error': 'Error retrieving pricing information'}), 500

        # Get or create time slot with transaction
        try:
            # Start transaction
            db.session.begin_nested()
            
            # Get the time slot with row-level locking
            time_slot = TimeSlot.query.filter_by(
                date=booking_date,
                slot_time=data['timeSlot'],
                ticket_type=data['ticketType']
            ).with_for_update().first()

            if not time_slot:
                time_slot = TimeSlot(
                    date=booking_date,
                    slot_time=data['timeSlot'],
                    capacity=50,
                    ticket_type=data['ticketType'],
                    booked_count=0
                )
                db.session.add(time_slot)
                db.session.flush()

            logger.info('Time slot found/created - Current capacity: %d, Booked: %d', 
                       time_slot.capacity, time_slot.booked_count)
            
            if time_slot.booked_count + total_visitors > time_slot.capacity:
                db.session.rollback()
                return jsonify({
                    'error': f'Not enough capacity available. Requested: {total_visitors}, Available: {time_slot.capacity - time_slot.booked_count}'
                }), 400

            time_slot.booked_count += total_visitors
            
            # Create the booking
            booking = Booking(
                date=booking_date,
                email=data['email'],
                nationality=data['nationality'],
                adults=adults,
                children=children,
                ticket_type=data['ticketType'],
                time_slot=data['timeSlot'],
                total_amount=float(total_amount),
                status='pending',
                payment_status='pending'
            )
            
            db.session.add(booking)
            db.session.commit()
            
            logger.info('Booking created successfully - ID: %s', booking.booking_id)
            
            return jsonify({
                'success': True,
                'booking_id': booking.booking_id,
                'amount': total_amount
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error('Error in booking transaction: %s', str(e))
            logger.error('Traceback: %s', traceback.format_exc())
            return jsonify({'error': 'Failed to process booking'}), 500
            
    except Exception as e:
        logger.error('Error in create_booking: %s', str(e))
        logger.error('Traceback: %s', traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Configuration from environment
BACKEND_PORT = int(os.getenv('BACKEND_PORT', 5002))

# Configure Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

def init_db():
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("Database tables created successfully")
            
            # Clear existing pricing data
            try:
                Pricing.query.delete()
                db.session.commit()
                print("Cleared existing pricing data")
            except Exception as e:
                print(f"Error clearing pricing data: {str(e)}")
                db.session.rollback()
            
            # Add default pricing
            today = datetime.now().date()
            future_date = today + timedelta(days=365)
            
            default_pricing = [
                Pricing(
                    nationality='Local',
                    ticket_type='Regular',
                    adult_price=20.0,
                    child_price=10.0,
                    effective_from=today,
                    effective_to=future_date
                ),
                Pricing(
                    nationality='Foreign',
                    ticket_type='Regular',
                    adult_price=30.0,
                    child_price=15.0,
                    effective_from=today,
                    effective_to=future_date
                )
            ]
            
            for pricing in default_pricing:
                try:
                    db.session.add(pricing)
                    db.session.commit()
                    print(f"Added pricing for {pricing.nationality} - {pricing.ticket_type}")
                except Exception as e:
                    print(f"Error adding pricing: {str(e)}")
                    db.session.rollback()
            
            # Verify pricing data
            all_pricing = Pricing.query.all()
            print(f"Total pricing records: {len(all_pricing)}")
            for p in all_pricing:
                print(f"Pricing: {p.nationality} - {p.ticket_type}: Adult=${p.adult_price}, Child=${p.child_price}")
                
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            traceback.print_exc()
            raise

def send_booking_confirmation(booking):
    try:
        msg = Message(
            'Museum Visit Booking Confirmation',
            recipients=[booking.email]
        )
        msg.body = f'''
Dear Visitor,

Your museum visit booking has been confirmed!

Booking Details:
---------------
Booking ID: {booking.booking_id}
Date: {booking.date.strftime('%Y-%m-%d')}
Time Slot: {booking.time_slot}
Number of Adults: {booking.adults}
Number of Children: {booking.children}
Total Amount: ${booking.total_amount}

Please keep this email for your records. You will need to show this booking ID when you arrive at the museum.

Thank you for choosing to visit our museum!

Best regards,
Museum Team
'''
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# Serve main HTML file
@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

# Booking endpoints
@app.route('/api/bookings/availability/<date>', methods=['GET'])
def check_availability(date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        slots = TimeSlot.query.filter_by(date=date_obj).all()
        return jsonify([{
            'time': slot.slot_time,
            'available': slot.capacity - slot.booked_count,
            'ticket_type': slot.ticket_type
        } for slot in slots])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'error': 'Date parameter is required'}), 400
            
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            
        # Get time slots for the date
        slots = TimeSlot.query.filter_by(date=date_obj).all()
        
        # If no slots exist for this date, create them
        if not slots:
            morning_slot = TimeSlot(
                date=date_obj,
                slot_time='10:00 AM',
                capacity=50,  # Back to 50 slots
                ticket_type='Regular',
                booked_count=0
            )
            afternoon_slot = TimeSlot(
                date=date_obj,
                slot_time='2:00 PM',
                capacity=50,  # Back to 50 slots
                ticket_type='Regular',
                booked_count=0
            )
            
            try:
                db.session.add(morning_slot)
                db.session.add(afternoon_slot)
                db.session.commit()
                print(f"Successfully created time slots for {date_obj}")  # Add debug logging
                slots = [morning_slot, afternoon_slot]
            except Exception as e:
                db.session.rollback()
                print(f"Error creating time slots: {str(e)}")
                return jsonify({'error': 'Failed to create time slots'}), 500
        
        # Get bookings for the date
        bookings = Booking.query.filter_by(date=date_obj).all()
        
        return jsonify({
            'slots': [{
                'time': slot.slot_time,
                'available': slot.capacity - slot.booked_count,
                'capacity': slot.capacity,
                'booked': slot.booked_count,
                'ticket_type': slot.ticket_type
            } for slot in slots],
            'bookings': [booking.to_dict() for booking in bookings]
        })
        
    except Exception as e:
        print(f"Error in get_bookings: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/bookings/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    try:
        booking = Booking.query.filter_by(booking_id=booking_id).first()
        if not booking:
            return jsonify({
                'status': 'error',
                'message': 'Booking not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': {
                'id': booking.booking_id,
                'date': booking.date.strftime('%Y-%m-%d'),
                'time_slot': booking.time_slot,
                'adult_count': booking.adults,
                'child_count': booking.children,
                'total_amount': float(booking.total_amount),
                'status': booking.status.capitalize(),
                'payment_status': booking.payment_status
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/bookings', methods=['GET'])
def get_user_bookings():
    try:
        # Get all bookings ordered by date
        bookings = Booking.query.order_by(Booking.date.desc()).all()
        
        bookings_data = []
        for booking in bookings:
            try:
                # Get associated time slot
                time_slot = TimeSlot.query.get(booking.time_slot_id)
                
                # Get associated payment
                payment = Payment.query.filter_by(booking_id=booking.id).first()
                
                # Get pricing info
                pricing = Pricing.query.filter_by(
                    nationality=booking.nationality,
                    ticket_type=booking.ticket_type
                ).first()
                
                # Calculate total amount
                adult_total = booking.adults * (pricing.adult_price if pricing else 0)
                child_total = booking.children * (pricing.child_price if pricing else 0)
                total_amount = adult_total + child_total
                
                booking_info = {
                    'id': booking.id,
                    'date': booking.date.strftime('%Y-%m-%d'),
                    'created_at': booking.created_at.strftime('%Y-%m-%d %I:%M %p'),
                    'nationality': booking.nationality,
                    'adults': booking.adults,
                    'children': booking.children,
                    'ticket_type': booking.ticket_type,
                    'time_slot': f"{time_slot.start_time.strftime('%I:%M %p')} - {time_slot.end_time.strftime('%I:%M %p')}" if time_slot else 'N/A',
                    'status': booking.status,
                    'payment_status': payment.status if payment else 'Not Initiated',
                    'payment_id': payment.payment_id if payment else None,
                    'total_amount': f"${total_amount:.2f}",
                    'pricing_details': {
                        'adult_price': f"${pricing.adult_price:.2f}" if pricing else 'N/A',
                        'child_price': f"${pricing.child_price:.2f}" if pricing else 'N/A',
                        'adult_total': f"${adult_total:.2f}",
                        'child_total': f"${child_total:.2f}"
                    }
                }
                bookings_data.append(booking_info)
            except Exception as e:
                print(f"Error processing booking {booking.id}: {str(e)}")
                continue
        
        return jsonify({'success': True, 'bookings': bookings_data})
    except Exception as e:
        print(f"Error fetching bookings: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to fetch bookings. Please try again later.'}), 500

@app.route('/api/bookings', methods=['GET'])
def get_bookings_by_date():
    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'error': 'Date parameter is required'}), 400

        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Initialize slots for this date if they don't exist
        existing_slots = TimeSlot.query.filter_by(date=date_obj).all()
        if not existing_slots:
            morning_slot = TimeSlot(
                date=date_obj,
                slot_time='10:00 AM',
                capacity=50,
                ticket_type='Regular',
                booked_count=0
            )
            afternoon_slot = TimeSlot(
                date=date_obj,
                slot_time='2:00 PM',
                capacity=50,
                ticket_type='Regular',
                booked_count=0
            )
            
            db.session.add(morning_slot)
            db.session.add(afternoon_slot)
            try:
                db.session.commit()
                existing_slots = [morning_slot, afternoon_slot]
            except Exception as e:
                db.session.rollback()
                print(f"Error creating slots: {str(e)}")
                return jsonify({'error': 'Failed to create time slots'}), 500
        
        slots_info = []
        for slot in existing_slots:
            available = slot.capacity - slot.booked_count
            slots_info.append({
                'time': slot.slot_time,
                'available': available,
                'total': slot.capacity,
                'booked': slot.booked_count,
                'ticket_type': slot.ticket_type
            })
        
        return jsonify({
            'date': date_str,
            'slots': slots_info
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        print(f"Error getting bookings for date: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Pricing endpoint
@app.route('/api/pricing', methods=['GET'])
def get_pricing():
    try:
        nationality = request.args.get('nationality')
        ticket_type = request.args.get('ticketType')
        date_str = request.args.get('date')
        
        if not all([nationality, ticket_type, date_str]):
            return jsonify({'error': 'Missing required parameters'}), 400
            
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
            
        pricing = Pricing.query.filter_by(
            nationality=nationality,
            ticket_type=ticket_type
        ).filter(
            Pricing.effective_from <= date_obj,
            Pricing.effective_to >= date_obj
        ).first()
        
        if not pricing:
            return jsonify({'error': 'No pricing found for the selected options'}), 404
            
        return jsonify({
            'adult_price': pricing.adult_price,
            'child_price': pricing.child_price
        })
        
    except Exception as e:
        print(f"Error in get_pricing: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Payment endpoints
@app.route('/api/payments/initialize', methods=['POST'])
def initialize_payment():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['booking_id', 'amount', 'payment_method']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
            
        booking = Booking.query.filter_by(booking_id=data['booking_id']).first()
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
            
        if booking.payment_status == 'completed':
            return jsonify({'error': 'Payment already completed'}), 400
            
        # Create payment record
        payment = Payment(
            booking_id=booking.booking_id,
            amount=data['amount'],
            payment_method=data['payment_method'],
            status='pending',
            transaction_id=str(uuid.uuid4())  # Generate a unique transaction ID
        )
        
        try:
            # Start a transaction
            db.session.begin_nested()
            
            db.session.add(payment)
            
            # For demo purposes, automatically mark payment as completed
            payment.status = 'completed'
            booking.payment_status = 'completed'
            booking.status = 'confirmed'
            
            # Update time slot capacity
            time_slot = TimeSlot.query.filter_by(
                date=booking.date,
                slot_time=booking.time_slot,
                ticket_type=booking.ticket_type
            ).first()
            
            if not time_slot:
                db.session.rollback()
                return jsonify({'error': 'Time slot not found'}), 404
                
            if time_slot.booked_count + 1 > time_slot.capacity:
                db.session.rollback()
                return jsonify({'error': 'Not enough capacity available'}), 400
                
            time_slot.booked_count += 1
            
            # Commit the transaction
            db.session.commit()
            
            # Only send confirmation email after successful payment and database updates
            email_sent = send_booking_confirmation(booking)
            if not email_sent:
                print("Warning: Failed to send confirmation email")
                # Don't fail the payment if email fails, but log it
            
            return jsonify({
                'success': True,
                'payment_id': payment.id,
                'status': payment.status,
                'transaction_id': payment.transaction_id
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error processing payment: {str(e)}")
            return jsonify({'error': 'Failed to process payment'}), 500
            
    except Exception as e:
        print(f"Error in initialize_payment: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/payments/<payment_id>/status', methods=['GET'])
def get_payment_status(payment_id):
    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        return jsonify(payment.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Calendar endpoints
@app.route('/api/calendar/monthly/<year>/<month>', methods=['GET'])
def get_calendar_data(year, month):
    try:
        print(f"Processing calendar request for {year}/{month}")
        
        # Convert string parameters to integers
        year = int(year)
        month = int(month)
        
        # Get the first and last day of the month
        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        print(f"Fetching slots between {first_day} and {last_day}")
        
        # Get all time slots for the month
        slots = TimeSlot.query.filter(
            TimeSlot.date >= first_day,
            TimeSlot.date <= last_day
        ).all()
        
        # Create calendar data
        calendar_data = {}
        current_date = first_day
        today = datetime.now().date()
        
        while current_date <= last_day:
            # Get slots for current date
            day_slots = [s for s in slots if s.date == current_date]
            
            # For future dates with no slots, create default slots
            if not day_slots and current_date >= today:
                try:
                    morning_slot = TimeSlot(
                        date=current_date,
                        slot_time='10:00 AM',
                        capacity=50,
                        ticket_type='Regular',
                        booked_count=0
                    )
                    afternoon_slot = TimeSlot(
                        date=current_date,
                        slot_time='2:00 PM',
                        capacity=50,
                        ticket_type='Regular',
                        booked_count=0
                    )
                    db.session.add(morning_slot)
                    db.session.add(afternoon_slot)
                    db.session.commit()
                    day_slots = [morning_slot, afternoon_slot]
                    print(f"Created default slots for {current_date}")
                except Exception as e:
                    print(f"Error creating slots for {current_date}: {str(e)}")
                    db.session.rollback()
            
            # Calculate availability
            if day_slots:
                slot_data = []
                total_available = 0
                total_capacity = 0
                
                for slot in day_slots:
                    available = slot.capacity - slot.booked_count
                    total_available += available
                    total_capacity += slot.capacity
                    
                    slot_data.append({
                        'time': slot.slot_time,
                        'available': available,
                        'capacity': slot.capacity,
                        'booked': slot.booked_count
                    })
                
                # Determine overall status
                if total_capacity == 0:
                    status = 'unavailable'
                elif total_available == 0:
                    status = 'full'
                elif total_available <= 5:  # Limited availability threshold
                    status = 'limited'
                else:
                    status = 'available'
                    
                calendar_data[current_date.strftime('%Y-%m-%d')] = {
                    'status': status,
                    'slots': slot_data,
                    'total_available': total_available,
                    'total_capacity': total_capacity
                }
            else:
                calendar_data[current_date.strftime('%Y-%m-%d')] = {
                    'status': 'unavailable',
                    'slots': [],
                    'total_available': 0,
                    'total_capacity': 0
                }
            
            current_date += timedelta(days=1)
        
        return jsonify(calendar_data)
        
    except Exception as e:
        print(f"Error processing calendar request: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(port=BACKEND_PORT, debug=True)
