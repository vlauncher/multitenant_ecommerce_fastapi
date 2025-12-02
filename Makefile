.PHONY: run celery celery-dev redis dev prod test clean

# Run the FastAPI app
run:
	python main.py

# Start Celery worker (production mode)
celery:
	python celery_worker.py

# Start Redis server
redis:
	redis-server

# Development mode: start Redis and Celery in background
dev:
	@echo "Starting Redis in background..."
	redis-server --daemonize yes --port 6379
	@echo "Starting Celery worker in background..."
	python celery_worker.py &

# Production mode: start all services
prod:
	@echo "Starting Redis..."
	redis-server --daemonize yes --port 6379
	@echo "Starting Celery worker..."
	python celery_worker.py &
	@echo "Starting FastAPI app..."
	python main.py

# Stop all services
stop:
	@echo "Stopping Celery workers..."
	pkill -f "celery worker" || true
	@echo "Stopping Redis..."
	pkill -f "redis-server" || true

# Run tests with in-memory SQLite
test:
	TESTING=True pytest tests/ -v

# Run tests with coverage
test-coverage:
	TESTING=True pytest tests/ -v --cov=. --cov-report=html

# Run specific test file
test-auth:
	TESTING=True pytest tests/test_auth.py -v

test-multitenancy:
	TESTING=True pytest tests/test_multitenancy.py -v

# Run tests in watch mode (requires pytest-watch)
test-watch:
	TESTING=True ptw tests/ -v

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -f *.db
	rm -rf .pytest_cache
	rm -rf htmlcov