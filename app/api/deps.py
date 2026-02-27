from typing import Generator
from app.db.session import SessionLocal
from sqlalchemy.orm import Session
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from app.db.models.api_key import ApiKey
from app.core.security import verify_secret
import structlog

logger = structlog.get_logger(__name__)

def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session for the duration of a request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

API_KEY_HEADER = "X-API-Key"

def get_project_id_from_api_key(
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
) -> int:
    """Dependency that extracts the project ID from the provided API key in the request header"""
    if not x_api_key:
        logger.warning("auth_missing_api_key")
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    
    if "." not in x_api_key:
        logger.warning("auth_invalid_format", key_prefix="invalid")
        raise HTTPException(status_code=403, detail="Invalid API key format")
    
    prefix, secret = x_api_key.split(".", 1)
    
    row = db.execute(
        select(ApiKey).where(
            ApiKey.prefix == prefix,
            ApiKey.revoked_at.is_(None)
        )
    ).scalar_one_or_none()
    
    if not row:
        logger.warning("auth_key_not_found", key_prefix=prefix)
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    if not verify_secret(secret, row.hashed_secret):
        logger.warning(
            "auth_invalid_secret",
            key_prefix=prefix,
            project_id=row.project_id
        )
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    logger.debug("auth_success", key_prefix=prefix, project_id=row.project_id)
    return row.project_id