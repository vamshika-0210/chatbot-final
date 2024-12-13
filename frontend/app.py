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
FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', 5003))

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
    print("\n")
    print("="*50)
    print("BOOKING CREATION STARTED")
    print("="*50)
    print("\nRequest Data:", request.get_data())
    print("Request JSON:", request.get_json())
    
    try:
        # Validate request data
        if not request.is_json:
            print("ERROR: No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
            
        booking_data = request.get_json()
        if not booking_data:
            print("ERROR: Empty JSON data")
            return jsonify({'error': 'Empty booking data'}), 400
            
        required_fields = ['email', 'date', 'timeSlot', 'adults']
        missing_fields = [field for field in required_fields if field not in booking_data]
        if missing_fields:
            print(f"ERROR: Missing required fields: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
            
        print("\nValidated booking data:", booking_data)
        
        # Send booking request to gateway
        gateway_url = f"{GATEWAY_URL}/api/bookings/create"
        print(f"\nSending booking request to gateway: {gateway_url}")
        print("Request data:", booking_data)
        
        response = requests.post(
            gateway_url,
            json=booking_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print("\nGateway Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if not response.ok:
            print("ERROR: Gateway returned error response")
            return jsonify(response.json()), response.status_code
            
        # Process gateway response
        try:
            gateway_response = response.json()
        except ValueError as e:
            print("ERROR: Invalid JSON response from gateway")
            return jsonify({'error': 'Invalid response from gateway'}), 500
            
        booking_id = gateway_response.get('booking_id')
        if not booking_id:
            print("ERROR: No booking ID in gateway response")
            print("Gateway response:", gateway_response)
            return jsonify({'error': 'No booking ID received'}), 500
            
        print("\nBooking created successfully")
        print("Booking ID:", booking_id)
        
        # Send confirmation email
        print("\n")
        print("="*50)
        print("SENDING CONFIRMATION EMAIL")
        print("="*50)
        
        email_data = {
            'to_email': booking_data['email'],
            'booking_id': booking_id,
            'booking_details': {
                'date': booking_data['date'],
                'timeSlot': booking_data['timeSlot'],
                'adults': int(booking_data.get('adults', 0)),
                'children': int(booking_data.get('children', 0)),
                'amount': float(gateway_response.get('amount', 0))
            }
        }
        
        print("\nEmail request data:", email_data)
        
        try:
            email_url = f"{GATEWAY_URL}/api/email/send"
            print(f"\nSending email request to: {email_url}")
            
            email_response = requests.post(
                email_url,
                json=email_data,
                headers={'Content-Type': 'application/json'}
            )
            
            print("\nEmail Response:")
            print(f"Status Code: {email_response.status_code}")
            print(f"Response Headers: {dict(email_response.headers)}")
            print(f"Response Body: {email_response.text}")
            
            if not email_response.ok:
                print("WARNING: Failed to send email")
                gateway_response['email_status'] = 'failed'
            else:
                print("Email sent successfully")
                gateway_response['email_status'] = 'sent'
                
        except Exception as e:
            print("\nERROR: Exception while sending email:")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            gateway_response['email_status'] = 'failed'
            
        print("\n")
        print("="*50)
        print("BOOKING CREATION COMPLETED")
        print("="*50)
        return jsonify(gateway_response), 200
        
    except Exception as e:
        print("\nERROR: Unexpected exception:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

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

@app.route('/test', methods=['GET'])
def test_endpoint():
    print("TEST ENDPOINT CALLED")
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("=== Frontend Server Starting ===")
    print(f"Frontend URL: http://localhost:{FRONTEND_PORT}")
    print(f"Gateway URL: {GATEWAY_URL}")
    socketio.run(app, port=FRONTEND_PORT, debug=True)
