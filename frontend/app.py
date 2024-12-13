from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import requests
import os
from dotenv import load_dotenv

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
        print("Frontend: Received booking data:", request.json)  # Debug log
        
        # Send booking request to gateway
        response = requests.post(
            f"{GATEWAY_URL}/api/bookings/create",
            json=request.json,
            headers={'Content-Type': 'application/json'}
        )
        
        if not response.ok:
            print(f"Frontend: Gateway error - {response.status_code}")  # Debug log
            error_data = response.json()
            return jsonify(error_data), response.status_code
            
        # Get the response data
        booking_data = response.json()
        print("Frontend: Booking created successfully:", booking_data)  # Debug log
        
        # Send confirmation email
        try:
            print("Frontend: Attempting to send email...")  # Debug log
            email_data = {
                'to_email': request.json['email'],
                'booking_id': booking_data.get('booking_id'),
                'booking_details': {
                    'date': request.json.get('date'),
                    'timeSlot': request.json.get('timeSlot'),
                    'adults': request.json.get('adults'),
                    'children': request.json.get('children'),
                    'amount': request.json.get('amount'),
                    'email': request.json.get('email')
                }
            }
            print("Frontend: Email data:", email_data)  # Debug log
            
            email_response = requests.post(
                f"{GATEWAY_URL}/api/email/send",
                json=email_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if not email_response.ok:
                print(f"Frontend: Email sending failed - Status: {email_response.status_code}")
                print(f"Frontend: Email error response:", email_response.json())
            else:
                print("Frontend: Email sent successfully")
                
        except Exception as email_error:
            print(f"Frontend: Email error - {str(email_error)}")
            # Don't fail the booking if email fails
            
        return jsonify(booking_data), response.status_code
        
    except requests.RequestException as e:
        print(f"Frontend: Request exception - {str(e)}")  # Debug log
        return jsonify({'error': 'Gateway service unavailable', 'message': str(e)}), 503
    except Exception as e:
        print(f"Frontend: Unexpected error - {str(e)}")  # Debug log
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
