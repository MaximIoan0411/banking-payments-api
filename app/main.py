from fastapi import FastAPI

from app.routers import auth
from app.routers import accounts
from app.routers import transactions

app = FastAPI(title="Banking Payments API")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}