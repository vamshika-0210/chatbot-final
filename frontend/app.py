from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import requests
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
socketio = SocketIO(app)

# Service URLs from environment
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://localhost:5001')
FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', 5000))

@app.route('/')
def index():
    return render_template('index.html', gateway_url=GATEWAY_URL)

@app.route('/heritage')
def heritage():
    return render_template('heritage.html')
#decorator function used in flask to handle socket connections
@socketio.on('connect')
def handle_connect():
    emit('response', {'message': 'Welcome to the Museum Ticket Booking System!'})

@socketio.on('send_message')
def handle_message(data):
    try:
        # Send message to API Gateway
        response = requests.post(
            f"{GATEWAY_URL}/api/chat/message",
            json={'message': data['message']}
        )
        response_data = response.json()
        
        # Process the response based on intent
        if response_data.get('intent') == 'booking':
            emit('response', {
                'message': response_data['message'],
                'action': response_data['next_action']
            })
        else:
            emit('response', {'message': response_data['message']})
    except Exception as e:
        emit('error', {'message': str(e)})

@app.route('/api/booking/create', methods=['POST'])
def create_booking():
    try:
        print("\n=== Booking Creation Started ===")
        print("Frontend: Received booking data:", request.json)
        
        # Send booking request to gateway
        gateway_url = f"{GATEWAY_URL}/api/bookings/create"
        print(f"Frontend: Sending booking request to {gateway_url}")
        
        response = requests.post(
            gateway_url,
            json=request.json,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Frontend: Booking response status: {response.status_code}")
        print(f"Frontend: Booking response data: {response.text}")
        
        if not response.ok:
            print(f"Frontend: Gateway error - {response.status_code}")
            error_data = response.json()
            return jsonify(error_data), response.status_code
            
        # Get the response data
        booking_data = response.json()
        print("Frontend: Booking created successfully:", booking_data)
        
        # Extract booking ID from response
        booking_id = None
        if isinstance(booking_data, dict):
            booking_id = booking_data.get('booking_id') or booking_data.get('id')
            if not booking_id and 'success' in booking_data:
                # Try to find id in nested data
                for key, value in booking_data.items():
                    if isinstance(value, dict) and ('id' in value or 'booking_id' in value):
                        booking_id = value.get('id') or value.get('booking_id')
                        break
        
        print(f"Extracted booking ID: {booking_id}")
        if not booking_id:
            print("WARNING: Could not extract booking ID from response:", booking_data)
            booking_id = "UNKNOWN"
        
        # Prepare email data
        try:
            print("\n=== Email Sending Started ===")
            email_data = {
                'to_email': request.json.get('email'),
                'booking_id': booking_id,
                'booking_details': {
                    'date': request.json.get('date'),
                    'timeSlot': request.json.get('timeSlot'),
                    'adults': int(request.json.get('adults', 0)),
                    'children': int(request.json.get('children', 0)),
                    'amount': float(booking_data.get('amount', 0)),
                    'email': request.json.get('email')
                }
            }
            print("Email data prepared:", email_data)
            
            # Validate email data
            if not email_data['to_email']:
                print("Frontend: Missing email address!")
                return jsonify({'error': 'Email address is required'}), 400
            
            # Send email request to gateway
            email_url = f"{GATEWAY_URL}/api/email/send"
            print(f"\nSending email request to {email_url}")
            print(f"Email request headers: {{'Content-Type': 'application/json'}}")
            print(f"Email request data: {email_data}")
            
            email_response = requests.post(
                email_url,
                json=email_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"\nEmail Response:")
            print(f"Status Code: {email_response.status_code}")
            print(f"Response Headers: {dict(email_response.headers)}")
            print(f"Response Text: {email_response.text}")
            
            try:
                email_response_data = email_response.json()
                print(f"Response JSON: {email_response_data}")
            except:
                print("Could not parse email response as JSON")
            
            if not email_response.ok:
                print(f"Frontend: Email sending failed - Status: {email_response.status_code}")
                print(f"Frontend: Email error response:", email_response.text)
            else:
                print("Frontend: Email sent successfully")
                
        except Exception as email_error:
            print("\n=== Email Error Details ===")
            print(f"Error Type: {type(email_error).__name__}")
            print(f"Error Message: {str(email_error)}")
            print("Traceback:")
            print(traceback.format_exc())
            # Don't fail the booking if email fails
            
        print("=== Booking Creation Completed ===\n")
        return jsonify(booking_data), response.status_code
        
    except requests.RequestException as e:
        print(f"Frontend: Request exception - {str(e)}")
        return jsonify({'error': 'Gateway service unavailable', 'message': str(e)}), 503
    except Exception as e:
        print(f"Frontend: Unexpected error - {str(e)}")
        print(f"Frontend: Error traceback:", traceback.format_exc())
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@app.route('/api/booking/<booking_id>', methods=['GET'])
def get_booking(booking_id):
    try:
        response = requests.get(f"{GATEWAY_URL}/api/bookings/{booking_id}")
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        return jsonify({'error': 'Gateway service unavailable'}), 503

@app.route('/api/calendar/monthly/<year>/<month>', methods=['GET'])
def get_calendar(year, month):
    try:
        print(f"Frontend: Fetching calendar for {year}/{month}")  # Debug log
        response = requests.get(
            f"{GATEWAY_URL}/api/calendar/monthly/{year}/{month}",
            headers={'Content-Type': 'application/json'}
        )
        if not response.ok:
            print(f"Frontend: Gateway error - {response.status_code}")  # Debug log
            return jsonify(response.json()), response.status_code
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        print(f"Frontend: Request exception - {str(e)}")  # Debug log
        return jsonify({'error': 'Gateway service unavailable'}), 503

if __name__ == '__main__':
    socketio.run(app, port=FRONTEND_PORT, debug=True)
