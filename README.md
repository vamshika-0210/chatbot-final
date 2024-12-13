# Museum Ticket Booking System

A microservices-based ticket booking system with a chatbot interface for museum visits.

## Architecture

- Frontend Service: Flask-based chatbot interface
- API Gateway: Flask middleware service
- Backend Service: Flask service with SQLite database
- Communication: REST APIs and WebSocket

## Services

1. Frontend Service (Port 5003)
   - Chatbot UI
   - Real-time chat using WebSocket
   - Booking interface
   - Status checking

2. API Gateway (Port 5001)
   - Request routing
   - Authentication
   - Rate limiting
   - Service orchestration

3. Backend Service (Port 5002)
   - Database operations
   - Business logic
   - Payment processing
   - QR code generation

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run services:
```bash
# Terminal 1 - Frontend
python frontend/app.py

# Terminal 2 - Gateway
python gateway/app.py

# Terminal 3 - Backend
python backend/app.py
```

## Features

- Real-time chat interface
- Interactive booking flow
- Dynamic pricing based on nationality
- Time slot management
- QR code generation
- Payment processing
- Booking status tracking

## Security

- JWT authentication
- Rate limiting
- Input validation
- CORS protection
- Session management

## API Documentation

See `docs/api.md` for detailed API documentation.
