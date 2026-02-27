from pydantic import BaseModel

class ApiKeyCreateOut(BaseModel):
    api_key: str
    prefix: str
    project_id: int
