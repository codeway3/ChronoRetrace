import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.infrastructure.database.models import (
    User,
    UserWatchlist,
    UserWatchlistItem,
)
from app.infrastructure.database.session import get_db
from app.schemas.auth_schemas import ApiResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic模型
class WatchlistCreate(BaseModel):
    """创建自选股列表请求"""

    name: str = Field(..., min_length=1, max_length=100, description="列表名称")
    description: str | None = Field(None, max_length=500, description="列表描述")
    is_public: bool = Field(False, description="是否公开")


class WatchlistUpdate(BaseModel):
    """更新自选股列表请求"""

    name: str | None = Field(None, min_length=1, max_length=100, description="列表名称")
    description: str | None = Field(None, max_length=500, description="列表描述")
    is_public: bool | None = Field(None, description="是否公开")


class WatchlistItemAdd(BaseModel):
    """添加股票到自选股请求"""

    stock_code: str = Field(..., description="股票代码")
    notes: str | None = Field(None, max_length=500, description="备注")


class WatchlistItemUpdate(BaseModel):
    """更新自选股股票请求"""

    notes: str | None = Field(None, max_length=500, description="备注")


class WatchlistResponse(BaseModel):
    """自选股列表响应"""

    id: int
    name: str
    description: str | None
    is_public: bool
    is_default: bool
    items_count: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class WatchlistItemResponse(BaseModel):
    """自选股股票响应"""

    id: int
    stock_code: str
    stock_name: str | None
    notes: str | None
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchlistDetailResponse(BaseModel):
    """自选股列表详情响应"""

    id: int
    name: str
    description: str | None
    is_public: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime | None
    items: list[WatchlistItemResponse]

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=list[WatchlistResponse])
async def get_user_watchlists(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取用户的自选股列表"""
    try:
        watchlists = (
            db.query(UserWatchlist)
            .filter(UserWatchlist.user_id == current_user.id)
            .order_by(UserWatchlist.is_default.desc(), UserWatchlist.created_at.asc())
            .all()
        )

        # 计算每个列表的股票数量
        result = []
        for watchlist in watchlists:
            items_count = (
                db.query(UserWatchlistItem)
                .filter(UserWatchlistItem.watchlist_id == watchlist.id)
                .count()
            )

            watchlist_data = {
                "id": watchlist.id,
                "name": watchlist.name,
                "description": watchlist.description,
                "is_public": watchlist.is_public,
                "is_default": watchlist.is_default,
                "items_count": items_count,
                "created_at": watchlist.created_at,
                "updated_at": watchlist.updated_at,
            }
            result.append(watchlist_data)

        return result

    except Exception as e:
        logger.error(f"获取用户自选股列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取自选股列表失败") from None


@router.post("/", response_model=WatchlistResponse)
async def create_watchlist(
    watchlist_data: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的自选股列表"""
    try:
        # 检查用户是否已有同名列表
        existing = (
            db.query(UserWatchlist)
            .filter(
                and_(
                    UserWatchlist.user_id == current_user.id,
                    UserWatchlist.name == watchlist_data.name,
                )
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="已存在同名的自选股列表"
            )

        # 检查用户列表数量限制（最多10个）
        user_watchlists_count = (
            db.query(UserWatchlist)
            .filter(UserWatchlist.user_id == current_user.id)
            .count()
        )

        if user_watchlists_count >= 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="自选股列表数量已达上限（10个）",
            )

        # 创建新列表
        new_watchlist = UserWatchlist(
            user_id=current_user.id,
            name=watchlist_data.name,
            description=watchlist_data.description,
            is_public=watchlist_data.is_public,
            is_default=False,  # 新创建的列表默认不是默认列表
        )

        db.add(new_watchlist)
        db.commit()
        db.refresh(new_watchlist)

        return {
            "id": new_watchlist.id,
            "name": new_watchlist.name,
            "description": new_watchlist.description,
            "is_public": new_watchlist.is_public,
            "is_default": new_watchlist.is_default,
            "items_count": 0,
            "created_at": new_watchlist.created_at,
            "updated_at": new_watchlist.updated_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建自选股列表失败: {e}")
        raise HTTPException(status_code=500, detail="创建自选股列表失败") from None


@router.get("/default", response_model=WatchlistDetailResponse)
async def get_default_watchlist(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """获取用户的默认自选股列表"""
    # 查找默认列表
    default_watchlist = (
        db.query(UserWatchlist)
        .filter(
            and_(UserWatchlist.user_id == current_user.id, UserWatchlist.is_default)
        )
        .first()
    )

    # 如果没有默认列表，创建一个
    if not default_watchlist:
        default_watchlist = UserWatchlist(
            user_id=current_user.id,
            name="我的自选股",
            description="默认自选股列表",
            is_public=False,
            is_default=True,
        )
        db.add(default_watchlist)
        db.commit()
        db.refresh(default_watchlist)

    # 获取列表中的股票
    items = (
        db.query(UserWatchlistItem)
        .filter(UserWatchlistItem.watchlist_id == default_watchlist.id)
        .order_by(UserWatchlistItem.added_at.desc())
        .all()
    )

    # 构造响应数据
    items_data = []
    for item in items:
        # 这里可以从股票表获取股票名称等信息
        # stock = db.query(StockInfo).filter(StockInfo.ts_code == item.stock_code).first()
        item_data = {
            "id": item.id,
            "stock_code": item.stock_code,
            "stock_name": None,  # 暂时为空，后续可以从股票表获取
            "notes": item.notes,
            "added_at": item.added_at,
        }
        items_data.append(item_data)

    return {
        "id": default_watchlist.id,
        "name": default_watchlist.name,
        "description": default_watchlist.description,
        "is_public": default_watchlist.is_public,
        "is_default": default_watchlist.is_default,
        "created_at": default_watchlist.created_at,
        "updated_at": default_watchlist.updated_at,
        "items": items_data,
    }


@router.get("/{watchlist_id}", response_model=WatchlistDetailResponse)
async def get_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定的自选股列表详情"""
    watchlist = (
        db.query(UserWatchlist)
        .filter(
            and_(
                UserWatchlist.id == watchlist_id,
                or_(UserWatchlist.user_id == current_user.id, UserWatchlist.is_public),
            )
        )
        .first()
    )

    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="自选股列表不存在或无权访问"
        )

    # 获取列表中的股票
    items = (
        db.query(UserWatchlistItem)
        .filter(UserWatchlistItem.watchlist_id == watchlist_id)
        .order_by(UserWatchlistItem.added_at.desc())
        .all()
    )

    items_data = []
    for item in items:
        item_data = {
            "id": item.id,
            "stock_code": item.stock_code,
            "stock_name": None,
            "notes": item.notes,
            "added_at": item.added_at,
        }
        items_data.append(item_data)

    return {
        "id": watchlist.id,
        "name": watchlist.name,
        "description": watchlist.description,
        "is_public": watchlist.is_public,
        "is_default": watchlist.is_default,
        "created_at": watchlist.created_at,
        "updated_at": watchlist.updated_at,
        "items": items_data,
    }


@router.put("/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: int,
    watchlist_data: WatchlistUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新自选股列表信息"""
    watchlist = (
        db.query(UserWatchlist)
        .filter(
            and_(
                UserWatchlist.id == watchlist_id,
                UserWatchlist.user_id == current_user.id,
            )
        )
        .first()
    )

    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="自选股列表不存在或无权修改"
        )

    # 检查名称是否重复
    if watchlist_data.name and watchlist_data.name != watchlist.name:
        existing = (
            db.query(UserWatchlist)
            .filter(
                and_(
                    UserWatchlist.user_id == current_user.id,
                    UserWatchlist.name == watchlist_data.name,
                    UserWatchlist.id != watchlist_id,
                )
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="已存在同名的自选股列表"
            )

    # 更新字段
    update_data = watchlist_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(watchlist, field, value)

    watchlist.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(watchlist)

    # 计算股票数量
    items_count = (
        db.query(UserWatchlistItem)
        .filter(UserWatchlistItem.watchlist_id == watchlist.id)
        .count()
    )

    return {
        "id": watchlist.id,
        "name": watchlist.name,
        "description": watchlist.description,
        "is_public": watchlist.is_public,
        "is_default": watchlist.is_default,
        "items_count": items_count,
        "created_at": watchlist.created_at,
        "updated_at": watchlist.updated_at,
    }


@router.delete("/{watchlist_id}", response_model=ApiResponse)
async def delete_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除自选股列表"""
    watchlist = (
        db.query(UserWatchlist)
        .filter(
            and_(
                UserWatchlist.id == watchlist_id,
                UserWatchlist.user_id == current_user.id,
            )
        )
        .first()
    )

    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="自选股列表不存在或无权删除"
        )

    # 不能删除默认列表
    if watchlist.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除默认自选股列表"
        )

    # 删除列表中的所有股票
    db.query(UserWatchlistItem).filter(
        UserWatchlistItem.watchlist_id == watchlist_id
    ).delete()

    # 删除列表
    db.delete(watchlist)
    db.commit()

    return ApiResponse(success=True, message="自选股列表删除成功")


@router.post("/{watchlist_id}/items", response_model=WatchlistItemResponse)
async def add_stock_to_watchlist(
    watchlist_id: int,
    item_data: WatchlistItemAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """添加股票到自选股列表"""
    # 检查列表是否存在且属于当前用户
    watchlist = (
        db.query(UserWatchlist)
        .filter(
            and_(
                UserWatchlist.id == watchlist_id,
                UserWatchlist.user_id == current_user.id,
            )
        )
        .first()
    )

    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="自选股列表不存在或无权访问"
        )

    # 检查股票是否已在列表中
    existing_item = (
        db.query(UserWatchlistItem)
        .filter(
            and_(
                UserWatchlistItem.watchlist_id == watchlist_id,
                UserWatchlistItem.stock_code == item_data.stock_code,
            )
        )
        .first()
    )

    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="股票已在自选股列表中"
        )

    # 检查列表中股票数量限制（最多100只）
    items_count = (
        db.query(UserWatchlistItem)
        .filter(UserWatchlistItem.watchlist_id == watchlist_id)
        .count()
    )

    if items_count >= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自选股列表中股票数量已达上限（100只）",
        )

    # 添加股票到列表
    new_item = UserWatchlistItem(
        watchlist_id=watchlist_id,
        stock_code=item_data.stock_code,
        notes=item_data.notes,
    )

    db.add(new_item)

    # 更新列表的修改时间
    watchlist.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(new_item)

    return {
        "id": new_item.id,
        "stock_code": new_item.stock_code,
        "stock_name": None,
        "notes": new_item.notes,
        "added_at": new_item.added_at,
    }


@router.put("/{watchlist_id}/items/{item_id}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    watchlist_id: int,
    item_id: int,
    item_data: WatchlistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新自选股列表中的股票信息"""
    # 检查项目是否存在且属于当前用户的列表
    item = (
        db.query(UserWatchlistItem)
        .join(UserWatchlist)
        .filter(
            and_(
                UserWatchlistItem.id == item_id,
                UserWatchlistItem.watchlist_id == watchlist_id,
                UserWatchlist.user_id == current_user.id,
            )
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="自选股项目不存在或无权修改"
        )

    # 更新备注
    if item_data.notes is not None:
        item.notes = item_data.notes

    # 更新列表的修改时间
    watchlist = db.query(UserWatchlist).filter(UserWatchlist.id == watchlist_id).first()
    if watchlist:
        watchlist.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "stock_code": item.stock_code,
        "stock_name": None,
        "notes": item.notes,
        "added_at": item.added_at,
    }


@router.delete("/{watchlist_id}/items/{item_id}", response_model=ApiResponse)
async def remove_stock_from_watchlist(
    watchlist_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """从自选股列表中移除股票"""
    # 检查项目是否存在且属于当前用户的列表
    item = (
        db.query(UserWatchlistItem)
        .join(UserWatchlist)
        .filter(
            and_(
                UserWatchlistItem.id == item_id,
                UserWatchlistItem.watchlist_id == watchlist_id,
                UserWatchlist.user_id == current_user.id,
            )
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="自选股项目不存在或无权删除"
        )

    # 删除项目
    db.delete(item)

    # 更新列表的修改时间
    watchlist = db.query(UserWatchlist).filter(UserWatchlist.id == watchlist_id).first()
    if watchlist:
        watchlist.updated_at = datetime.utcnow()

    db.commit()

    return ApiResponse(success=True, message="股票已从自选股列表中移除")


@router.get("/public/popular", response_model=PaginatedResponse)
async def get_popular_watchlists(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """获取热门公开自选股列表"""
    # 查询公开的自选股列表，按创建时间排序
    query = (
        db.query(UserWatchlist)
        .filter(UserWatchlist.is_public)
        .order_by(UserWatchlist.created_at.desc())
    )

    total = query.count()
    offset = (page - 1) * size
    watchlists = query.offset(offset).limit(size).all()

    # 构造响应数据
    watchlist_data = []
    for watchlist in watchlists:
        # 获取创建者信息
        creator = db.query(User).filter(User.id == watchlist.user_id).first()

        # 计算股票数量
        items_count = (
            db.query(UserWatchlistItem)
            .filter(UserWatchlistItem.watchlist_id == watchlist.id)
            .count()
        )

        data = {
            "id": watchlist.id,
            "name": watchlist.name,
            "description": watchlist.description,
            "creator_name": creator.username if creator else "未知用户",
            "items_count": items_count,
            "created_at": watchlist.created_at.isoformat(),
        }
        watchlist_data.append(data)

    pages = (total + size - 1) // size

    return PaginatedResponse(
        items=watchlist_data, total=total, page=page, size=size, pages=pages
    )
