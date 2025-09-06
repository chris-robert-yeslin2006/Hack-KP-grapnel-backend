# System constants

VALID_HASH_TYPES = ["SHA256", "MD5", "PHASH"]
VALID_SOURCE_SYSTEMS = ["trace", "grapnel", "takedown"]
VALID_SEVERITY_LEVELS = ["low", "medium", "high", "critical"]
VALID_NOTIFICATION_TYPES = ["hash_match", "alert", "update"]

# Rate limiting
DEFAULT_RATE_LIMIT = 100
HASH_LOOKUP_RATE_LIMIT = 100
HASH_REGISTER_RATE_LIMIT = 50

# Cache TTL (in seconds)
HASH_LOOKUP_CACHE_TTL = 300  # 5 minutes
SYSTEM_STATS_CACHE_TTL = 300  # 5 minutes
WEBHOOK_CACHE_TTL = 3600     # 1 hour

# Notification settings
MAX_RETRY_ATTEMPTS = 3
NOTIFICATION_TIMEOUT = 10    # seconds