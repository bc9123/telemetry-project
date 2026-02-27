import secrets
import bcrypt

def generate_api_key(prefix_length: int = 8, secret_length: int = 32) -> tuple[str, str, str]:
    """
    Returns (raw_key, prefix, hashed_secret)
    raw_key format: "<prefix>.<secret>"
    """
    
    prefix = secrets.token_hex(prefix_length // 2)
    secret = secrets.token_urlsafe(secret_length)
    hashed = hashed_secret(secret)
    raw_key = f"{prefix}.{secret}"
    
    return raw_key, prefix, hashed

def hashed_secret(secret: str) -> str:
    """Hash the secret using bcrypt."""
    return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_secret(secret: str, stored_hashed: str) -> bool:
    """Verify the provided secret against the stored hashed value."""
    return bcrypt.checkpw(secret.encode("utf-8"), stored_hashed.encode("utf-8"))