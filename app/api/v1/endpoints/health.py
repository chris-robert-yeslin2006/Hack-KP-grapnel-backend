from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.core.database import db_manager
from app.core.redis import redis_manager

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    System health check
    
    Returns the health status of all system components including
    database, Redis, and external service connectivity.
    """
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {}
    }
    
    # Check database connectivity
    try:
        db_healthy = await db_manager.health_check()
        health_status["components"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "type": "supabase"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "type": "supabase",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Redis connectivity
    try:
        await redis_manager.connect()
        test_key = "health_check_test"
        await redis_manager.set(test_key, "test_value", expire=10)
        test_value = await redis_manager.get(test_key)
        await redis_manager.delete(test_key)
        
        redis_healthy = test_value == "test_value"
        health_status["components"]["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "type": "redis"
        }
        
        if not redis_healthy:
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "type": "redis",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Overall system status
    if health_status["status"] == "healthy":
        return health_status
    else:
        raise HTTPException(status_code=503, detail=health_status)

@router.get("/ready")
async def readiness_check():
    """
    Readiness check for load balancers
    
    Returns 200 if the service is ready to accept requests
    """
    
    try:
        # Quick checks for essential services
        db_healthy = await db_manager.health_check()
        
        if not db_healthy:
            raise HTTPException(status_code=503, detail="Database not ready")
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")