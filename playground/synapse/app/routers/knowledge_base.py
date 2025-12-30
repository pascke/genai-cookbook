import uuid

from typing import List, Optional
from fastapi import Query, APIRouter, Depends, HTTPException, status

from ..schemas import KnowledgeBase, KnowledgeBaseSearch
from ..services.knowledge_base import KnowledgeBaseService

router = APIRouter(prefix="/knowledge-groups/{knowledge_group_id}/knowledge-bases", tags=["knowledge-bases"])

@router.post(
    "/", 
    status_code=status.HTTP_201_CREATED,
    response_model=List[uuid.UUID]
)
async def create(knowledge_group_id: uuid.UUID, documents: List[KnowledgeBase], service: KnowledgeBaseService = Depends()) -> List[uuid.UUID]:
    try:
        ids = await service.create(knowledge_group_id, documents)
        return ids
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.get("/-/search", response_model=List[KnowledgeBaseSearch])
async def search(
    knowledge_group_id: uuid.UUID,
    q: str = Query(..., description="Query text"),
    k: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    threshold: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance Threshold (minimum similarity 0..1). Ex.: 0.40",
    ),
    service: KnowledgeBaseService = Depends(),
) -> List[KnowledgeBaseSearch]:
    try:
        return await service.search(knowledge_group_id, q, k, threshold)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))