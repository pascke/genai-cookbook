from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import Identity, AgentCreate
from ..services.agent import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post(
    "/", 
    status_code=status.HTTP_201_CREATED,
    response_model=Identity
)
async def create(schema: AgentCreate, service: AgentService = Depends()) -> Identity:
    try:
        id = await service.create(schema)
        return Identity(id=id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))