import uuid

from typing import List, Tuple, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import KnowledgeBaseModel

class KnowledgeBaseRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self, 
        knowledge_group_id: uuid.UUID,
        qemb: List[float], 
        k: int = 5, 
        threshold: Optional[float] = None
    ) -> List[Tuple[KnowledgeBaseModel, float, float]]:
        
        stmt = select(
            KnowledgeBaseModel.id,
            KnowledgeBaseModel.name,
            KnowledgeBaseModel.content,
            KnowledgeBaseModel.embedding.cosine_distance(qemb).label("distance")
        )

        stmt = stmt.where(KnowledgeBaseModel.knowledge_group_id == knowledge_group_id)

        if threshold is not None:
            distance = 1 - threshold
            stmt = stmt.where(KnowledgeBaseModel.embedding.cosine_distance(qemb) <= distance)

        stmt = stmt.order_by(KnowledgeBaseModel.embedding.cosine_distance(qemb)).limit(k)

        result = await self.session.execute(stmt)
        rows = result.mappings().all()
        return [
            (KnowledgeBaseModel(**{k: v for k, v in row.items() if k != "distance"}), row["distance"], 1 - row["distance"])
            for row in rows
        ]