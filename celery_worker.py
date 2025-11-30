#!/usr/bin/env python3
"""
Celery worker script for the multitenant ecommerce app.
Run this script to start the Celery worker for email processing.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    from core.celery import celery_app
    
    # Start Celery worker
    celery_app.start([
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--without-gossip",
        "--without-mingle",
        "--without-heartbeat",
    ])
