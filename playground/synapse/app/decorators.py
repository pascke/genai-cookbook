from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession

def transactional(fn):
    @wraps(fn)
    async def wrapper(self, *args, **kwargs):
        session: AsyncSession = getattr(self, "session")
        async with session.begin():
            return await fn(self, *args, **kwargs)
    return wrapper
