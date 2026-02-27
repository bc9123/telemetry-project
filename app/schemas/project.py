from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str

class ProjectOut(BaseModel):
    id: int
    org_id: int
    name: str

    model_config = {"from_attributes": True}
