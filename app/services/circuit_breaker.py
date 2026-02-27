# app/services/circuit_breaker.py
from datetime import datetime, timedelta, timezone
from redis import Redis
from app.settings import settings

class WebhookCircuitBreaker:
    """
    Circuit breaker for webhook URLs using Redis for state storage.
    
    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(self, redis_client: Redis, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.redis = redis_client
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
    
    def _key_state(self, url: str) -> str:
        return f"circuit:state:{url}"
    
    def _key_failures(self, url: str) -> str:
        return f"circuit:failures:{url}"
    
    def _key_opened_at(self, url: str) -> str:
        return f"circuit:opened_at:{url}"
    
    def is_open(self, url: str) -> bool:
        """Check if circuit is open (blocking requests)"""
        state = self.redis.get(self._key_state(url))
        
        if state == b"open":
            # Check if recovery timeout has passed
            opened_at = self.redis.get(self._key_opened_at(url))
            if opened_at:
                opened_time = datetime.fromisoformat(opened_at.decode())
                if datetime.now(timezone.utc) - opened_time > timedelta(seconds=self.recovery_timeout):
                    # Transition to half-open
                    self.redis.set(self._key_state(url), "half_open", ex=3600)
                    return False
            return True
        
        return False
    
    def record_success(self, url: str):
        """Record successful request"""
        state = self.redis.get(self._key_state(url))
        
        if state == b"half_open":
            # Recovery successful, close circuit
            self.redis.delete(self._key_state(url))
            self.redis.delete(self._key_failures(url))
            self.redis.delete(self._key_opened_at(url))
        else:
            # Reset failure counter
            self.redis.delete(self._key_failures(url))
    
    def record_failure(self, url: str):
        """Record failed request"""
        failures = self.redis.incr(self._key_failures(url))
        self.redis.expire(self._key_failures(url), 300)  # 5 min window
        
        if failures >= self.failure_threshold:
            # Open circuit
            self.redis.set(self._key_state(url), "open", ex=3600)
            self.redis.set(
                self._key_opened_at(url),
                datetime.now(timezone.utc).isoformat(),
                ex=3600
            )
            return True
        
        return False
    
    def get_stats(self, url: str) -> dict:
        """Get circuit breaker stats for monitoring"""
        return {
            "state": (self.redis.get(self._key_state(url)) or b"closed").decode(),
            "failures": int(self.redis.get(self._key_failures(url)) or 0),
            "opened_at": (self.redis.get(self._key_opened_at(url)) or b"").decode(),
        }