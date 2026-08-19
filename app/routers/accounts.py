from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_account
from app.models.account import Account
from app.schemas.account import AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/me", response_model=AccountOut)
async def get_my_balance(account: Annotated[Account, Depends(get_current_account)]):
    return account