# app/schemas/rule.py
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional

RuleScope = Literal["ALL", "EXPLICIT", "TAG"]
RuleOp = Literal[">", ">=", "<", "<="]

class RuleCreate(BaseModel):
    name: str
    metric: str
    operator: RuleOp = ">"
    threshold: float

    window_n: int = Field(default=1, ge=1, le=10000)
    required_k: int = Field(default=1, ge=1, le=10000)

    cooldown_seconds: int = Field(default=300, ge=0, le=86400)
    enabled: bool = True
    scope: RuleScope = "ALL"
    tag: Optional[str] = None
    
    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope == "TAG" and not self.tag:
            raise ValueError("tag is required when scope is TAG")
        if self.scope != "TAG" and self.tag is not None:
            raise ValueError("tag must be null unless scope is TAG")
        return self

class RuleOut(BaseModel):
    id: int
    project_id: int
    name: str
    metric: str
    operator: str
    threshold: float
    window_n: int
    required_k: int
    cooldown_seconds: int
    enabled: bool
    scope: str
    tag: Optional[str] = None

    model_config = {"from_attributes": True}

class RuleAssignDevices(BaseModel):
    device_ids: list[int] = Field(default_factory=list)

class RuleUpdate(BaseModel):
    name: str | None = None
    metric: str | None = None
    operator: RuleOp | None = None
    threshold: float | None = None
    window_n: int | None = None
    required_k: int | None = None
    cooldown_seconds: int | None = None
    scope: RuleScope | None = None
    tag: str | None = None
    enabled: bool | None = None