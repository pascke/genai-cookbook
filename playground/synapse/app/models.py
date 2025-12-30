import uuid
from datetime import datetime
from typing import Any, List, Dict, Optional

from pydantic import BaseModel
from pgvector.sqlalchemy import Vector
from sqlmodel import SQLModel, Field, Relationship

from sqlalchemy import Index
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class LLMConfig(BaseModel):
    name: str
    settings: Optional[Dict[str, Any]] = None

class LLMConfigType(TypeDecorator):
    impl = JSONB
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, LLMConfig):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        raise TypeError(f"Unsupported type for LLMConfigType: {type(value)}")
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return LLMConfig(**value)

class AgentModel(SQLModel, table=True):
    __tablename__ = "agents"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        sa_type=PG_UUID(as_uuid=True),
    )
    name: str = Field(nullable=False)
    description: str = Field(nullable=False)
    instructions: str = Field(nullable=False)
    model: LLMConfig = Field(
        nullable=False,
        sa_type=LLMConfigType,
    )

class NestedAgentModel(SQLModel, table=True):
    __tablename__ = "nested_agents"
    agent_id: uuid.UUID = Field(
        nullable=False,
        sa_type=PG_UUID(as_uuid=True),
        foreign_key="agents.id",
        primary_key=True,
    )
    sub_agent_id: uuid.UUID = Field(
        nullable=False,
        sa_type=PG_UUID(as_uuid=True),
        foreign_key="agents.id",
        primary_key=True,
    )
    created_at: datetime = Field(nullable=False, default_factory=datetime.now)

class SessionModel(SQLModel, table=True):
    __tablename__ = "sessions"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        sa_type=PG_UUID(as_uuid=True),
    )
    created_at: datetime = Field(nullable=False, default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None, nullable=True)

class MessageModel(SQLModel, table=True):
    __tablename__ = "messages"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        sa_type=PG_UUID(as_uuid=True),
    )
    session_id: uuid.UUID = Field(
        foreign_key="session.id",
        nullable=False,
        index=True,
        sa_type=PG_UUID(as_uuid=True),
    )
    content: str = Field(nullable=False)
    labels: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSONB)
    created_at: datetime = Field(nullable=False, default_factory=datetime.now)

class KnowledgeGroupModel(SQLModel, table=True):
    __tablename__ = "knowledge_groups"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        sa_type=PG_UUID(as_uuid=True),
    )
    name: str = Field(nullable=False)
    description: str = Field(nullable=True)

class KnowledgeBaseModel(SQLModel, table=True):
    __tablename__ = "knowledge_bases"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        sa_type=PG_UUID(as_uuid=True),
    )
    knowledge_group_id: uuid.UUID = Field(
        foreign_key="knowledge_groups.id",
        nullable=False,
        index=True,
        sa_type=PG_UUID(as_uuid=True),
    )
    name: str = Field(nullable=False)
    content: str = Field(nullable=False)
    embedding: list[float] = Field(sa_type=Vector(dim=1536), nullable=False)