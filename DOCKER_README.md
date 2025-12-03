# Docker Setup Guide

This project now includes a Docker configuration for development and deployment.

## Prerequisites

- Docker
- Docker Compose

## Quick Start

1.  **Build and start services:**
    ```bash
    docker-compose up --build
    ```
    This will start:
    - `web`: The FastAPI application (available at http://localhost:8000)
    - `worker`: The Celery worker for background tasks
    - `db`: PostgreSQL database (exposed on port 5432)
    - `redis`: Redis message broker (exposed on port 6379)

2.  **Access the API:**
    Open http://localhost:8000/docs to see the Swagger UI.

3.  **Stop services:**
    ```bash
    docker-compose down
    ```
    To stop and remove volumes (reset database):
    ```bash
    docker-compose down -v
    ```

## Configuration

- The `docker-compose.yml` file sets up the environment variables for the containers.
- Database data is persisted in the `postgres_data` volume.
- The application runs with `DEBUG=True` and hot-reloading enabled by default in this configuration.

## CI/CD

A GitHub Actions workflow `.github/workflows/ci.yml` has been added to run tests automatically on push and pull requests to the `main` or `master` branches.
