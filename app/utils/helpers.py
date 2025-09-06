import hashlib
import hmac
from typing import Any, Dict

def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC signature for webhook security"""
    signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def validate_hash(hash_value: str, hash_type: str) -> bool:
    """Validate hash format based on type"""
    if hash_type.upper() == "SHA256":
        return len(hash_value) == 64 and all(c in "0123456789abcdef" for c in hash_value.lower())
    elif hash_type.upper() == "MD5":
        return len(hash_value) == 32 and all(c in "0123456789abcdef" for c in hash_value.lower())
    elif hash_type.upper() == "PHASH":
        return len(hash_value) <= 64  # More flexible for perceptual hashes
    return False