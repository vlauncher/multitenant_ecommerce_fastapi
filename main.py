import os
from fastapi import FastAPI
from dotenv import load_dotenv
from core.db import Base, engine
from core.celery import celery_app
from routes.auth import router as auth_router

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "FastAPI Microservice"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add OpenAPI security schemes for Bearer token authentication on docs/redoc
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    # Apply BearerAuth globally so docs/redoc require it
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Ensure tables exist (for dev/test; in prod use Alembic)
Base.metadata.create_all(bind=engine)

app.include_router(auth_router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": os.getenv("APP_NAME", "FastAPI Microservice"),
    }


@app.get("/celery-health")
async def celery_health_check():
    """Check Celery worker status"""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            return {"status": "healthy", "workers": len(stats)}
        else:
            return {"status": "no_workers", "message": "No Celery workers running"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
    )
