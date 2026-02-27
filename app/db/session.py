import time
import structlog
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.settings import settings

logger = structlog.get_logger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
)

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Store the start time of the query execution in the connection info."""
    conn.info.setdefault("query_start_time", []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Calculate the total execution time of the query and log if it exceeds the threshold."""
    total = time.time() - conn.info["query_start_time"].pop(-1)
    if total > 1.0:  # Log queries slower than 1 second
        logger.warning(
            "slow_query",
            duration_seconds=round(total, 3),
            query=statement[:200]  # Truncate long queries
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)