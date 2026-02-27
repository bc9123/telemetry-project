# app/db/models/rule.py
from app.db.base import Base
from typing import Literal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Float, ForeignKey, Index, Integer, String, Boolean

class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (
        Index("ix_rules_project_enabled", "project_id", "enabled"),
        Index("ix_rules_project_scope", "project_id", "scope")
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(4), nullable=False, default=">")
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    window_n: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    required_k: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scope: Mapped[Literal["ALL", "EXPLICIT", "TAG"]] = mapped_column(String(16), nullable=False, default="ALL")
    tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
