# app/api/rate_limits.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Header, Request

def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key from API key or fall back to IP"""
    # Try to get API key from header
    api_key = request.headers.get("X-API-Key")
    
    if api_key and "." in api_key:
        prefix = api_key.split(".")[0]
        return f"key:{prefix}"
    
    # Fall back to IP address
    return f"ip:{request.client.host if request.client else 'unknown'}"

# Create limiter with our custom key function
limiter = Limiter(key_func=get_rate_limit_key)

# Rate limit tiers
class RateLimits:
    # Critical - write endpoints
    INGESTION = "1000/minute;10000/hour"  # Burst + sustained
    WEBHOOK_CREATE = "50/hour"
    API_KEY_CREATE = "10/hour"
    RULE_CREATE = "100/hour"
    RULE_ASSIGN_DEVICES = "200/hour"
    
    # Important - potentially expensive reads
    DEVICE_CREATE = "100/hour"
    
    # Generous - normal operations
    STANDARD_READ = "5000/minute"
    STANDARD_WRITE = "500/minute"