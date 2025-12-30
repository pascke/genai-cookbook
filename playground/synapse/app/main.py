import os

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .routers import agent, knowledge_group, knowledge_base
from .settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.OPENAI_API_KEY and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    yield

app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.include_router(agent.router)
app.include_router(knowledge_group.router)
app.include_router(knowledge_base.router)