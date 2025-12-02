# Setup Guide

## Prerequisites

- Python 3.10+
- pip or poetry
- Redis (for development/production)
- PostgreSQL (for production)

## Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd multitenant_ecommerce_fastapi
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create environment files

**For development** (`.env.dev`):
```bash
DEBUG=True
TESTING=False
APP_NAME=FastAPI Ecommerce
APP_VERSION=1.0.0
DATABASE_URL=sqlite:///./db.sqlite3
JWT_SECRET=your-secret-key-here
REFRESH_SECRET=your-refresh-secret-here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@example.com
REDIS_URL=redis://localhost:6379/0
```

**For testing** (`.env.test`):
Already provided - uses in-memory SQLite

### 5. Initialize database (development)
```bash
python -c "from core.db import Base, engine; Base.metadata.create_all(bind=engine)"
```

## Running the Application

### Development Mode
```bash
# Start Redis (in another terminal)
redis-server

# Start the app
DEBUG=True python main.py
```

The app will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Testing
```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
make test-auth

# Watch mode (auto-rerun on changes)
make test-watch
```

### Production Mode
```bash
# Set environment variables
export DEBUG=False
export POSTGRES_DATABASE_URL=postgresql://user:password@localhost/dbname

# Start the app
python main.py
```

## Project Structure

```
multitenant_ecommerce_fastapi/
├── core/                    # Core application logic
│   ├── config.py           # Configuration management
│   ├── db.py               # Database setup
│   ├── tenancy.py          # Multitenancy logic
│   └── celery.py           # Celery configuration
├── models/                 # SQLAlchemy models
│   ├── user.py            # User model with roles
│   ├── store.py           # Store model (tenant)
│   ├── product.py         # Product model
│   ├── order.py           # Order model
│   └── ...
├── routes/                # API endpoints
│   ├── auth.py            # Authentication
│   ├── products.py        # Products
│   ├── orders.py          # Orders
│   └── ...
├── schemas/               # Pydantic schemas
├── services/              # Business logic
├── security/              # Security utilities
├── tests/                 # Test suite
│   ├── test_auth.py       # Auth tests
│   ├── test_multitenancy.py  # Multitenancy tests
│   └── ...
├── conftest.py            # Pytest configuration
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── Makefile              # Development commands
├── TESTING.md            # Testing guide
├── MULTITENANCY.md       # Multitenancy guide
└── SETUP.md              # This file
```

## Key Commands

### Development
```bash
make run          # Run the app
make dev          # Start Redis and Celery
make celery       # Start Celery worker
make redis        # Start Redis server
```

### Testing
```bash
make test              # Run all tests
make test-coverage     # Generate coverage report
make test-auth         # Run auth tests
make test-multitenancy # Run multitenancy tests
make test-watch        # Watch mode
```

### Maintenance
```bash
make clean        # Clean up artifacts
make stop         # Stop all services
```

## Database Environments

### Testing (In-Memory SQLite)
- **Speed**: < 1 second per test
- **Isolation**: Complete
- **Persistence**: None (fresh DB per test)
- **Command**: `make test`

### Development (File-Based SQLite)
- **Speed**: Fast
- **Isolation**: None (shared DB)
- **Persistence**: `db.sqlite3`
- **Command**: `DEBUG=True python main.py`

### Production (PostgreSQL)
- **Speed**: Optimized
- **Isolation**: None (shared DB)
- **Persistence**: Database server
- **Command**: `DEBUG=False python main.py`

## API Documentation

Once the app is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Authentication

### Register
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

### Use Token
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

## Multitenancy

### Create Store
```bash
curl -X POST http://localhost:8000/stores \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Store",
    "domain": "mystore.example.com"
  }'
```

### Access Store
```bash
curl -X GET http://localhost:8000/products \
  -H "Authorization: Bearer <token>" \
  -H "X-Store-Domain: mystore.example.com"
```

## Troubleshooting

### ModuleNotFoundError
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Database locked
```bash
# Clean up and restart
make clean
make test
```

### Redis connection error
```bash
# Start Redis
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

### Port already in use
```bash
# Use different port
python main.py --port 8001
```

## Next Steps

1. Read [TESTING.md](TESTING.md) for testing guide
2. Read [MULTITENANCY.md](MULTITENANCY.md) for multitenancy details
3. Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for what was added
4. Run tests: `make test`
5. Start development: `make dev`

## Support

For issues or questions:
1. Check the documentation files
2. Review test examples
3. Check API docs at `/docs`
