from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
import time

from app.schemas.hash_schemas import (
    HashLookupRequest, HashLookupResponse, HashRegisterRequest, 
    HashRegisterResponse, SourceSystem
)
from app.services.hash_service import hash_service
from app.core.redis import redis_manager

router = APIRouter()

@router.post("/lookup", response_model=HashLookupResponse)
async def lookup_hashes(
    request: HashLookupRequest,
    background_tasks: BackgroundTasks
):
    """
    Lookup hashes across all systems
    
    This endpoint allows you to search for hash values across all connected systems
    and returns information about where those hashes have been seen before.
    """
    
    # Rate limiting check
    rate_limit_key = f"rate_limit:{request.source_system.value}"
    current_requests = await redis_manager.increment_rate_limit(rate_limit_key)
    
    if current_requests > 100:  # 100 requests per minute per system
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )
    
    try:
        result = await hash_service.lookup_hashes(request)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error looking up hashes: {str(e)}"
        )

@router.post("/register", response_model=HashRegisterResponse)
async def register_hashes(
    hashes: List[HashRegisterRequest],
    source_system: SourceSystem,
    background_tasks: BackgroundTasks
):
    """
    Register new hashes in the system
    
    This endpoint allows systems to register new hash values they've discovered.
    The system will automatically check for matches across other connected systems.
    """
    
    if len(hashes) > 100:
        raise HTTPException(
            status_code=400,
            detail="Cannot register more than 100 hashes at once"
        )
    
    # Rate limiting check
    rate_limit_key = f"rate_limit:{source_system.value}"
    current_requests = await redis_manager.increment_rate_limit(rate_limit_key)
    
    if current_requests > 50:  # 50 registration requests per minute per system
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for hash registration. Try again later."
        )
    
    try:
        result = await hash_service.register_hashes(hashes, source_system.value)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error registering hashes: {str(e)}"
        )
@router.get("/stats")
async def get_hash_stats():
    """
    Get system statistics
    
    Returns overall statistics about the hash registry including
    total hashes, matches found, and system activity.
    """
    try:
        # Get cached stats first
        cached_stats = await redis_manager.get("system_stats")
        if cached_stats:
            return cached_stats
        
        # Query database for fresh stats
        from app.core.database import db_manager
        
        # Total hashes by system
        total_result = db_manager.supabase.table("hash_registry").select("source_system", count="exact").execute()

        
        # Recent matches (last 24 hours)
        from datetime import datetime, timedelta
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        recent_matches = db_manager.supabase.table('hash_matches').select('*').gte('detected_at', yesterday).execute()
        
        stats = {
            "total_hashes": total_result.count,
            "recent_matches": len(recent_matches.data),
            "systems_connected": len(set(row['source_system'] for row in total_result.data)),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Cache for 5 minutes
        await redis_manager.set("system_stats", stats, expire=300)
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stats: {str(e)}"
        )