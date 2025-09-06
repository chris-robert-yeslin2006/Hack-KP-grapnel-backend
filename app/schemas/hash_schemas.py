from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

class HashType(str, Enum):
    SHA256 = "SHA256"
    MD5 = "MD5"
    PHASH = "PHASH"

class SourceSystem(str, Enum):
    TRACE = "trace"
    GRAPNEL = "grapnel"
    TAKEDOWN = "takedown"

class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class HashRegisterRequest(BaseModel):
    hash_value: str = Field(..., min_length=8, max_length=64)
    hash_type: HashType
    source_id: str = Field(..., min_length=1, max_length=255)
    severity: SeverityLevel = SeverityLevel.MEDIUM
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('hash_value')
    def validate_hash_value(cls, v):
        # Remove any whitespace and convert to lowercase
        return v.strip().lower()

class HashLookupRequest(BaseModel):
    hashes: List[str] = Field(..., min_items=1, max_items=100)
    source_system: SourceSystem
    include_metadata: bool = False
    
    @validator('hashes')
    def validate_hashes(cls, v):
        # Clean and validate each hash
        cleaned_hashes = []
        for hash_val in v:
            cleaned = hash_val.strip().lower()
            if len(cleaned) < 8 or len(cleaned) > 64:
                raise ValueError(f"Hash {cleaned} must be between 8 and 64 characters")
            cleaned_hashes.append(cleaned)
        return cleaned_hashes

class HashMatch(BaseModel):
    hash: str
    found: bool
    sources: List[Dict[str, Any]] = []
    confidence_score: Optional[float] = None
    match_type: Optional[str] = None

class HashLookupResponse(BaseModel):
    matches: List[HashMatch]
    total_matches: int
    query_time: float
    cached: bool = False

class HashRegisterResponse(BaseModel):
    success: bool
    registered_count: int
    errors: List[str] = []
    hash_ids: List[str] = []

class HashRegistryItem(BaseModel):
    id: str
    hash_value: str
    hash_type: HashType
    source_system: SourceSystem
    source_id: str
    created_at: datetime
    severity_level: SeverityLevel
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True