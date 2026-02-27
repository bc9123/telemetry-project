from pydantic import BaseModel

class OrgCreate(BaseModel):
    name: str
    
class OrgOut(BaseModel):
    id: int
    name: str
    
    model_config = {"from_attributes": True}