import uuid

from openai import OpenAI
from fastapi import Depends
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas import KnowledgeBase, KnowledgeBaseSearch
from ..decorators import transactional
from ..models import KnowledgeBaseModel
from ..settings import settings
from ..database import get_session
from ..repositories.knowledge_base import KnowledgeBaseRepository

client = OpenAI()

class KnowledgeBaseService:

    def __init__(self, session: AsyncSession = Depends(get_session)):
        self.session = session
        self.embed_model = settings.EMBED_MODEL
        self.repository = KnowledgeBaseRepository(session)

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = client.embeddings.create(model=self.embed_model, input=texts)
        return [data.embedding for data in response.data]

    @transactional
    async def create(self, knowledge_group_id: uuid.UUID, documents: List[KnowledgeBase]) -> List[uuid.UUID]:
        embeddings = self.embed([document.content for document in documents])
        ids = []
        for document, embedding in zip(documents, embeddings):
            model = KnowledgeBaseModel(
                name=document.name,
                content=document.content,
                embedding=embedding,
                knowledge_group_id=knowledge_group_id
            )
            self.session.add(model)
            ids.append(model.id)
        return ids
    
    async def search(
        self, 
        knowledge_group_id: uuid.UUID,
        query: str, 
        k: int = 5, 
        threshold: Optional[float] = None
    ) -> List[KnowledgeBaseSearch]:
        [qemb] = self.embed([query])
        results = await self.repository.search(knowledge_group_id, qemb, k, threshold)
        return [
            KnowledgeBaseSearch(
                id=model.id,
                name=model.name,
                content=model.content,
                distance=distance,
                similarity=similarity
            )
            for model, distance, similarity in results
        ]