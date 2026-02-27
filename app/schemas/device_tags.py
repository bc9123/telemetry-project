from pydantic import BaseModel, Field

class DeviceTagsUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)