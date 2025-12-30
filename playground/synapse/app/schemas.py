import uuid

from typing import Any, List, Dict, Optional
from pydantic import BaseModel

class Identity(BaseModel):
    id: uuid.UUID

class LLMConfig(BaseModel):
    name: str
    settings: Optional[Dict[str, Any]] = None

class Agent(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    description: str
    instructions: str
    model: LLMConfig

class AgentCreate(Agent):
    sub_agents: Optional[List[uuid.UUID]] = None

class KnowledgeGroup(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    description: str

class KnowledgeBase(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    content: str

class KnowledgeBaseSearch(KnowledgeBase):
    distance: float
    similarity: float