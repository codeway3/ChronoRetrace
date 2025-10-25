"""
股票筛选器服务
"""

from typing import Any, cast

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select

from app.infrastructure.database.models import DailyStockMetrics, StockInfo
from app.schemas.screener import (
    ScreenerRequest,
    ScreenerResponse,
    ScreenerResultItem,
)


def _build_screener_query(
    db: Session, request: ScreenerRequest
) -> tuple[Select, list[Any]]:
    """构建筛选器查询"""
    StockInfoAlias = aliased(StockInfo)
    DailyStockMetricsAlias = aliased(DailyStockMetrics)

    # 使用 cast(Any, ...) 包裹列，避免 Pyright 将模型属性解析为原始类型（如 str/float），
    # 导致 select 实体类型不匹配的诊断错误。
    query = select(
        cast("Any", StockInfoAlias.ts_code).label("symbol"),
        cast("Any", StockInfoAlias.name),
        cast("Any", StockInfoAlias.market_type).label("market"),
        cast("Any", DailyStockMetricsAlias.market_cap),
        cast("Any", DailyStockMetricsAlias.close_price).label("price"),
        cast("Any", DailyStockMetricsAlias.pe_ratio),
        cast("Any", DailyStockMetricsAlias.pb_ratio),
        cast("Any", DailyStockMetricsAlias.dividend_yield),
    ).join(
        DailyStockMetricsAlias,
        cast("Any", StockInfoAlias.ts_code == DailyStockMetricsAlias.code),
    )

    filters = []
    for condition in request.conditions:
        field_name = condition.field
        operator = condition.operator
        value = condition.value

        # Determine which model to query based on the field
        if hasattr(StockInfo, field_name):
            model_alias = StockInfoAlias
        elif hasattr(DailyStockMetrics, field_name):
            model_alias = DailyStockMetricsAlias
        else:
            continue  # Or raise an exception for an invalid field

        column = cast("Any", getattr(model_alias, field_name))

        if operator in (">", "gt"):
            filters.append(column > value)
        elif operator in ("<", "lt"):
            filters.append(column < value)
        elif operator in (">=", "ge"):
            filters.append(column >= value)
        elif operator in ("<=", "le"):
            filters.append(column <= value)
        elif operator in ("=", "eq"):
            filters.append(column == value)
        elif operator in ("!=", "ne"):
            filters.append(column != value)
        elif operator == "in":
            filters.append(column.in_(value))
        elif operator == "not_in":
            filters.append(~column.in_(value))

    if filters:
        query = query.filter(and_(*filters))

    # Sorting
    if request.sort_by:
        sort_column: Any | None = None
        # Check both aliases for the sort_by attribute
        if hasattr(StockInfoAlias, request.sort_by):
            sort_column = cast("Any", getattr(StockInfoAlias, request.sort_by))
        elif hasattr(DailyStockMetricsAlias, request.sort_by):
            sort_column = cast("Any", getattr(DailyStockMetricsAlias, request.sort_by))

        if sort_column is not None:
            if request.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)

    return query, request.conditions


def screen_stocks(request: ScreenerRequest, db: Session) -> ScreenerResponse:
    """执行股票筛选"""
    query, filters_applied = _build_screener_query(db, request)

    count_query = select(func.count()).select_from(query.subquery())
    total_count = db.scalar(count_query)

    # 分页
    query = query.offset((request.page - 1) * request.size).limit(request.size)

    results_from_db = db.execute(query).all()

    results = []
    for r in results_from_db:
        results.append(
            ScreenerResultItem(
                code=getattr(r, "symbol", None),
                symbol=r.symbol,
                name=r.name,
                market=r.market,
                sector="N/A",  # 暂时硬编码
                market_cap=r.market_cap,
                price=r.price,
                change_percent=0.0,  # 暂时硬编码
                volume=0,  # 暂时硬编码
                pe_ratio=r.pe_ratio,
                pb_ratio=r.pb_ratio,
                dividend_yield=r.dividend_yield,
                additional_data={},
            )
        )

    return ScreenerResponse(
        items=results,
        total=total_count if total_count is not None else 0,
        page=request.page,
        size=request.size,
        pages=(
            (total_count + request.size - 1) // request.size
            if total_count and total_count > 0
            else 0
        ),
        filters_applied=filters_applied,
    )
