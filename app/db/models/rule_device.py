# app/db/models/rule_device.py
from app.db.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, Integer, UniqueConstraint, Index

class RuleDevice(Base):
    __tablename__ = "rule_devices"
    __table_args__ = (
        UniqueConstraint("rule_id", "device_id", name="uq_rule_device"),
        Index("ix_rule_devices_device_id", "device_id"),
        Index("ix_rule_devices_rule_id", "rule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id"), nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
