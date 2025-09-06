import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.database import db_manager
from app.core.redis import redis_manager
from app.schemas.hash_schemas import (
    HashRegisterRequest, HashLookupRequest, HashLookupResponse, 
    HashRegisterResponse, HashMatch
)

class HashService:
    def __init__(self):
        self.db = db_manager
        self.redis = redis_manager
    
    async def lookup_hashes(self, request: HashLookupRequest) -> HashLookupResponse:
        """Lookup hashes across all systems with caching"""
        start_time = time.time()
        matches = []
        cached_results = 0
        
        for hash_value in request.hashes:
            # Check cache first
            cached_result = await self.redis.get_cached_hash_lookup(hash_value)
            
            if cached_result:
                matches.append(HashMatch(**cached_result))
                cached_results += 1
            else:
                # Query database
                match_result = await self._query_hash_from_db(
                    hash_value, request.include_metadata
                )
                matches.append(match_result)
                
                # Cache the result
                await self.redis.cache_hash_lookup(
                    hash_value, match_result.dict()
                )
        
        query_time = time.time() - start_time
        
        return HashLookupResponse(
            matches=matches,
            total_matches=sum(1 for m in matches if m.found),
            query_time=query_time,
            cached=cached_results > 0
        )
    
    async def _query_hash_from_db(self, hash_value: str, include_metadata: bool = False) -> HashMatch:
        """Query single hash from database"""
        try:
            # Query Supabase
            query = self.db.supabase.table('hash_registry').select('*').eq('hash_value', hash_value)
            result = query.execute()
            
            if not result.data:
                return HashMatch(hash=hash_value, found=False)
            
            # Process sources
            sources = []
            for record in result.data:
                source_data = {
                    "system": record["source_system"],
                    "id": record["source_id"],
                    "severity": record["severity_level"],
                    "timestamp": record["created_at"]
                }
                
                if include_metadata and record.get("metadata"):
                    source_data["metadata"] = record["metadata"]
                
                if record.get("tags"):
                    source_data["tags"] = record["tags"]
                
                sources.append(source_data)
            
            return HashMatch(
                hash=hash_value,
                found=True,
                sources=sources
            )
            
        except Exception as e:
            print(f"Hash lookup error: {e}")
            return HashMatch(hash=hash_value, found=False)
    
    async def register_hashes(self, hashes: List[HashRegisterRequest], source_system: str) -> HashRegisterResponse:
        """Register multiple hashes in the system"""
        registered_count = 0
        errors = []
        hash_ids = []
        
        for hash_request in hashes:
            try:
                # Create new hash entry
                hash_id = await self._create_new_hash_entry(hash_request, source_system)
                
                if hash_id:
                    hash_ids.append(hash_id)
                    registered_count += 1
                    
                    # Invalidate cache for this hash
                    await self.redis.delete(f"hash_lookup:{hash_request.hash_value}")
                
            except Exception as e:
                error_msg = f"Failed to register hash {hash_request.hash_value}: {str(e)}"
                errors.append(error_msg)
        
        return HashRegisterResponse(
            success=len(errors) == 0,
            registered_count=registered_count,
            errors=errors,
            hash_ids=hash_ids
        )
    
    async def _create_new_hash_entry(self, hash_request: HashRegisterRequest, source_system: str) -> Optional[str]:
        """Create a new hash entry in the database"""
        hash_id = str(uuid.uuid4())
        
        data = {
            "id": hash_id,
            "hash_value": hash_request.hash_value,
            "hash_type": hash_request.hash_type.value,
            "source_system": source_system,
            "source_id": hash_request.source_id,
            "severity_level": hash_request.severity.value,
            "tags": hash_request.tags or [],
            "metadata": hash_request.metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = self.db.supabase.table('hash_registry').insert(data).execute()
            
            if result.data:
                return hash_id
            return None
        except Exception as e:
            print(f"Error creating hash entry: {e}")
            return None

hash_service = HashService()