from fastapi import FastAPI
from app.database import engine, Base
from app.routers import tasks

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
