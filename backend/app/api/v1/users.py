from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.security import get_current_active_user
from ...infrastructure.database.models import User
from ...infrastructure.database.session import get_db
from ...schemas.auth_schemas import UserResponse

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户资料"""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    user_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新用户资料"""
    # 这里可以添加更新用户资料的逻辑
    # 暂时返回当前用户信息
    return current_user
