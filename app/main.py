from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routers import auth
from app.routers import accounts
from app.routers import transactions
from app.routers import webhooks
from app.routers import admin
from app.scheduler import shutdown_scheduler, start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()

app = FastAPI(title="Banking Payments API", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(webhooks.router)
app.include_router(admin.router)



@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}