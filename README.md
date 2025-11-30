# Multitenant E-commerce FastAPI

A FastAPI-based multitenant e-commerce platform with JWT authentication, OTP verification, and asynchronous email processing.

## Features

- **User Authentication**: JWT-based authentication with access/refresh tokens
- **Email Verification**: OTP-based email verification system
- **Asynchronous Email**: Celery-powered email queue with fallback mechanism
- **Password Security**: bcrypt-based password hashing with proper length handling
- **Error Resilience**: Graceful handling of email failures without blocking registration

## Setup

1. **Install dependencies**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.dev .env
# Edit .env with your configuration
```

3. **Database setup**:
```bash
# The app uses SQLite by default for development
# Tables are created automatically on startup
```

## Running the Application

### Development Mode (with email fallback)

For development, the app uses synchronous email sending with debug output:

```bash
source venv/bin/activate
python main.py
```

### Production Mode (with Celery)

For production, run both the FastAPI app and Celery worker:

1. **Start Redis** (required for Celery):
```bash
# Install and start Redis
redis-server
```

2. **Start Celery worker**:
```bash
source venv/bin/activate
python celery_worker.py
```

3. **Start FastAPI app**:
```bash
source venv/bin/activate
python main.py
```

### Environment Variables

Key environment variables:

```bash
# Database
# Development (DEBUG=true): Uses SQLite by default
DATABASE_URL=sqlite:///./db.sqlite3

# Production (DEBUG=false): Uses PostgreSQL 
POSTGRES_DATABASE_URL=postgresql://user:password@localhost/dbname

# JWT Settings
JWT_SECRET=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Email Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use app-specific password for Gmail
SMTP_FROM=your-email@gmail.com

# Celery Settings
REDIS_URL=redis://localhost:6379/0
CELERY_ALWAYS_EAGER=false  # Set to 'true' for development without Redis

# App Settings
DEBUG=true                 # Controls database switching and other dev features
TESTING=false
PORT=8000
```

### Database Switching

The application automatically switches databases based on the `DEBUG` setting:

- **DEBUG=true (Development)**: Uses SQLite (`sqlite:///./db.sqlite3`)
- **DEBUG=false (Production)**: Uses PostgreSQL (`POSTGRES_DATABASE_URL`)

This makes it easy to develop with SQLite and deploy with PostgreSQL without code changes.

## Email Configuration

### Gmail Setup

1. Enable 2-factor authentication on your Gmail account
2. Generate an app-specific password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Create a new app password
3. Use the app password in `SMTP_PASSWORD`

### Development Mode

In development mode (`CELERY_ALWAYS_EAGER=true` or `TESTING=true`):
- Emails are printed to console instead of being sent
- No Redis required
- Synchronous execution for easier debugging

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/verify-otp` - Verify email with OTP
- `POST /auth/resend-otp` - Resend verification code
- `POST /auth/change-password` - Change password (authenticated)
- `POST /auth/reset-password/request` - Request password reset
- `POST /auth/reset-password/confirm` - Confirm password reset
- `POST /auth/refresh-token` - Refresh access token

### Health Checks
- `GET /health` - Application health check
- `GET /celery-health` - Celery worker status

## Error Handling

The system includes robust error handling:

1. **Email Failures**: Registration continues even if email sending fails
2. **SMTP Issues**: Graceful fallback to debug mode in development
3. **Password Length**: Automatic truncation to bcrypt's 72-byte limit
4. **Celery Unavailable**: Automatic fallback to synchronous email sending

## Testing

Run the test suite:

```bash
source venv/bin/activate
pytest tests/
```

## Architecture

- **FastAPI**: Web framework
- **SQLAlchemy**: ORM with SQLite for development
- **JWT**: Token-based authentication
- **Celery + Redis**: Asynchronous task queue
- **bcrypt**: Password hashing
- **SMTP**: Email delivery

The email system is designed to be resilient:
- Celery handles async email processing
- Fallback to synchronous sending if Celery unavailable
- Debug mode for development without external dependencies
- Graceful degradation when email services fail