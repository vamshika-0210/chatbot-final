import requests
import json
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

# Get SMTP configuration
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')

def test_smtp_directly():
    print("\n=== Testing Direct SMTP Connection ===")
    print(f"SMTP Configuration:")
    print(f"- Server: {SMTP_SERVER}")
    print(f"- Port: {SMTP_PORT}")
    print(f"- Username: {SMTP_USERNAME}")
    print(f"- Password: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'Not Set'}")
    print(f"- Sender: {SENDER_EMAIL}")
    
    try:
        # Create test message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = SMTP_USERNAME  # Send to self
        msg['Subject'] = 'SMTP Test Email'
        msg.attach(MIMEText('This is a test email to verify SMTP configuration.', 'plain'))
        
        print("\nConnecting to SMTP server...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(2)
        
        print("\nStarting TLS...")
        server.starttls()
        
        print("\nLogging in...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        print("\nSending test email...")
        server.send_message(msg)
        
        print("\nClosing connection...")
        server.quit()
        
        print("\nTest email sent successfully!")
        return True
    except Exception as e:
        print(f"\nError sending test email: {str(e)}")
        return False

def test_gateway_email():
    test_data = {
        "to_email": "vamshika0210@gmail.com",
        "booking_id": "test123",
        "booking_details": {
            "date": "2024-01-20",
            "timeSlot": "10:00 AM",
            "adults": 2,
            "children": 1,
            "amount": 100
        }
    }

    print("\n=== Testing Gateway Email Endpoint ===")
    print("1. Testing email configuration...")
    config_response = requests.get('http://localhost:5001/api/email/test')
    print("Configuration response:", config_response.json())

    print("\n2. Testing email sending...")
    email_response = requests.post(
        'http://localhost:5001/api/email/send',
        json=test_data,
        headers={'Content-Type': 'application/json'}
    )

    print("Status Code:", email_response.status_code)
    print("Response:", email_response.text)
    return email_response.ok

if __name__ == "__main__":
    print("=== Starting Email Tests ===")
    
    print("\nStep 1: Testing direct SMTP connection")
    smtp_success = test_smtp_directly()
    
    if smtp_success:
        print("\nStep 2: Testing gateway email endpoint")
        gateway_success = test_gateway_email()
        
        if gateway_success:
            print("\nAll tests passed successfully!")
        else:
            print("\nGateway email test failed!")
    else:
        print("\nSMTP test failed! Please check your email configuration.") 