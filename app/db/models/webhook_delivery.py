from datetime import datetime, timezone
from sqlalchemy import (
    DateTime, ForeignKey, Integer, String, UniqueConstraint, Index, Text
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint("alert_id", "webhook_id", name="uq_delivery_alert_webhook"),
        Index("ix_delivery_project_created", "project_id", "created_at"),
        Index("ix_delivery_project_status", "project_id", "status"),
        Index("ix_delivery_alert_id", "alert_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), nullable=False)
    webhook_id: Mapped[int] = mapped_column(ForeignKey("webhook_subscriptions.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)