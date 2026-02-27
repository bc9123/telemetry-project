from enum import Enum
from pydantic import BaseModel

class WebhookDeliveryStatus(str, Enum):
    pending = "pending"
    sending = "sending"
    retrying = "retrying"
    failed = "failed"
    success = "success"

class WebhookDeliveryOut(BaseModel):
    id: int
    project_id: int
    alert_id: int
    webhook_id: int
    status: WebhookDeliveryStatus
    attempts: int
    last_status_code: int | None
    last_error: str | None

    model_config = {"from_attributes": True}
