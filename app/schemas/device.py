from pydantic import BaseModel

class DeviceCreate(BaseModel):
    external_id: str
    name: str
    tags: list[str] = []

class DeviceOut(BaseModel):
    id: int
    project_id: int
    external_id: str
    name: str
    tags: list[str]

    model_config = {"from_attributes": True}
