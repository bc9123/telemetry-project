from pydantic import BaseModel, HttpUrl

class WebhookCreate(BaseModel):
    url: HttpUrl
    secret: str | None = None

class WebhookOut(BaseModel):
    id: int
    project_id: int
    url: str
    enabled: bool

    model_config = {"from_attributes": True}
