from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import time
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from app.core.config import settings
from app.core.redis import redis_manager
from app.api.v1.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await redis_manager.connect()
    yield
    # Shutdown
    await redis_manager.disconnect()

# Create FastAPI application
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Hash Intelligence Sharing API for Child Safety Systems",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*.yourdomain.com", "yourdomain.com"]
    )

# Add timing middleware for performance monitoring
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Add rate limiting middleware
@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    # Skip rate limiting for health checks
    if request.url.path in ["/api/v1/health", "/api/v1/ready"]:
        response = await call_next(request)
        return response
    
    # Extract client identifier (you might want to use API keys in production)
    client_id = request.client.host
    
    # Check rate limit
    current_requests = await redis_manager.increment_rate_limit(f"global:{client_id}")
    
    if current_requests > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum requests per minute reached."
        )
    
    response = await call_next(request)
    return response

# Include API routes
app.include_router(api_router, prefix=settings.api_v1_str)
# Mount static folder (for CSS, JS, images, etc.)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

@app.get("/")
async def root():
    return {
        "message": "Grapnel Hash Intelligence API",
        "version": settings.version,
        "status": "operational",
        "docs_url": "/docs" if settings.debug else "Documentation available to authorized users"
    }
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard_page():
    dashboard_file = Path(__file__).parent / "static" / "dashboard.html"
    return HTMLResponse(dashboard_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )