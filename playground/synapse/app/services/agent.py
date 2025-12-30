import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import AgentCreate
from ..decorators import transactional
from ..models import LLMConfig, AgentModel, NestedAgentModel
from ..database import get_session

class AgentService:

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session

    @transactional
    async def create(self, schema: AgentCreate) -> uuid.UUID:
                
        model = AgentModel(
            name=schema.name,
            description=schema.description,
            instructions=schema.instructions,
            model=LLMConfig(
                name=schema.model.name,
                settings=schema.model.settings
            )
        )

        self.session.add(model)

        if schema.sub_agents:
            for sub_agent_id in schema.sub_agents:
                self.session.add(
                    NestedAgentModel(
                        agent_id=model.id,
                        sub_agent_id=sub_agent_id
                    )
                )

        return model.id