from datetime import datetime
from pydantic import BaseModel, Field

class TelemetryEventIn(BaseModel):
    ts: datetime
    data: dict = Field(default_factory=dict, max_length=10_000)

class TelemetryBatchIn(BaseModel):
    device_external_id: str
    events: list[TelemetryEventIn]

class TelemetryEventOut(BaseModel):
    id: int
    device_id: int
    ts: datetime
    payload: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}