from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import Identity, KnowledgeGroup
from ..services.knowledge_group import KnowledgeGroupService

router = APIRouter(prefix="/knowledge-groups", tags=["knowledge-groups"])

@router.post(
    "/", 
    status_code=status.HTTP_201_CREATED,
    response_model=Identity
)
async def create(schema: KnowledgeGroup, service: KnowledgeGroupService = Depends()) -> Identity:
    try:
        id = await service.create(schema)
        return Identity(id=id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))