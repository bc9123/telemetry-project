# app/schemas/alert.py
from datetime import datetime
from pydantic import BaseModel, Field

class AlertOut(BaseModel):
    id: int
    device_id: int
    rule_id: int
    triggered_at: datetime
    details: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}
