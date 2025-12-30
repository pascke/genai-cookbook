import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import KnowledgeGroup
from ..decorators import transactional
from ..models import KnowledgeGroupModel
from ..database import get_session

class KnowledgeGroupService:

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session

    @transactional
    async def create(self, schema: KnowledgeGroup) -> uuid.UUID:
                
        model = KnowledgeGroupModel(
            name=schema.name,
            description=schema.description
        )

        self.session.add(model)
        
        return model.id