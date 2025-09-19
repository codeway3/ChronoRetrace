from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import AssetConfig, AssetSymbol, AssetMarketData, AssetScreenerTemplate, AssetBacktestTemplate
from app.schemas.asset_config import (
    AssetConfigCreate, AssetConfigUpdate, AssetConfigResponse,
    AssetSymbolCreate, AssetSymbolUpdate, AssetSymbolResponse,
    AssetMarketDataCreate, AssetMarketDataUpdate, AssetMarketDataResponse,
    AssetScreenerTemplateCreate, AssetScreenerTemplateUpdate, AssetScreenerTemplateResponse,
    AssetBacktestTemplateCreate, AssetBacktestTemplateUpdate, AssetBacktestTemplateResponse
)

router = APIRouter()

# Asset Config endpoints
@router.get("/configs", response_model=List[AssetConfigResponse])
def get_asset_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    asset_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取资产配置列表"""
    query = db.query(AssetConfig)

    if asset_type:
        query = query.filter(AssetConfig.asset_type == asset_type)
    if is_enabled is not None:
        query = query.filter(AssetConfig.is_enabled == is_enabled)

    configs = query.order_by(AssetConfig.sort_order, AssetConfig.id).offset(skip).limit(limit).all()
    return configs

@router.get("/configs/{config_id}", response_model=AssetConfigResponse)
def get_asset_config(config_id: int, db: Session = Depends(get_db)):
    """获取单个资产配置"""
    config = db.query(AssetConfig).filter(AssetConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Asset config not found")
    return config

@router.post("/configs", response_model=AssetConfigResponse)
def create_asset_config(config: AssetConfigCreate, db: Session = Depends(get_db)):
    """创建资产配置"""
    # Check if asset_type already exists
    existing = db.query(AssetConfig).filter(AssetConfig.asset_type == config.asset_type).first()
    if existing:
        raise HTTPException(status_code=400, detail="Asset type already exists")

    db_config = AssetConfig(**config.dict())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.put("/configs/{config_id}", response_model=AssetConfigResponse)
def update_asset_config(config_id: int, config: AssetConfigUpdate, db: Session = Depends(get_db)):
    """更新资产配置"""
    db_config = db.query(AssetConfig).filter(AssetConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Asset config not found")

    update_data = config.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_config, field, value)

    db.commit()
    db.refresh(db_config)
    return db_config

@router.delete("/configs/{config_id}")
def delete_asset_config(config_id: int, db: Session = Depends(get_db)):
    """删除资产配置"""
    db_config = db.query(AssetConfig).filter(AssetConfig.id == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Asset config not found")

    db.delete(db_config)
    db.commit()
    return {"message": "Asset config deleted successfully"}

# Asset Symbol endpoints
@router.get("/symbols", response_model=List[AssetSymbolResponse])
def get_asset_symbols(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    asset_type: Optional[str] = None,
    exchange: Optional[str] = None,
    sector: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_tradable: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取资产标的列表"""
    query = db.query(AssetSymbol)

    if asset_type:
        query = query.filter(AssetSymbol.asset_type == asset_type)
    if exchange:
        query = query.filter(AssetSymbol.exchange == exchange)
    if sector:
        query = query.filter(AssetSymbol.sector == sector)
    if is_active is not None:
        query = query.filter(AssetSymbol.is_active == is_active)
    if is_tradable is not None:
        query = query.filter(AssetSymbol.is_tradable == is_tradable)
    if search:
        query = query.filter(
            (AssetSymbol.symbol.ilike(f"%{search}%")) |
            (AssetSymbol.name.ilike(f"%{search}%"))
        )

    symbols = query.order_by(AssetSymbol.symbol).offset(skip).limit(limit).all()
    return symbols

@router.get("/symbols/{symbol_id}", response_model=AssetSymbolResponse)
def get_asset_symbol(symbol_id: int, db: Session = Depends(get_db)):
    """获取单个资产标的"""
    symbol = db.query(AssetSymbol).filter(AssetSymbol.id == symbol_id).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="Asset symbol not found")
    return symbol

@router.post("/symbols", response_model=AssetSymbolResponse)
def create_asset_symbol(symbol: AssetSymbolCreate, db: Session = Depends(get_db)):
    """创建资产标的"""
    db_symbol = AssetSymbol(**symbol.dict())
    db.add(db_symbol)
    db.commit()
    db.refresh(db_symbol)
    return db_symbol

@router.put("/symbols/{symbol_id}", response_model=AssetSymbolResponse)
def update_asset_symbol(symbol_id: int, symbol: AssetSymbolUpdate, db: Session = Depends(get_db)):
    """更新资产标的"""
    db_symbol = db.query(AssetSymbol).filter(AssetSymbol.id == symbol_id).first()
    if not db_symbol:
        raise HTTPException(status_code=404, detail="Asset symbol not found")

    update_data = symbol.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_symbol, field, value)

    db.commit()
    db.refresh(db_symbol)
    return db_symbol

# Market Data endpoints
@router.get("/market-data", response_model=List[AssetMarketDataResponse])
def get_market_data(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    asset_type: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取市场数据"""
    query = db.query(AssetMarketData)

    if asset_type:
        query = query.filter(AssetMarketData.asset_type == asset_type)
    if symbol:
        query = query.filter(AssetMarketData.symbol == symbol)
    if start_date:
        query = query.filter(AssetMarketData.trade_date >= start_date)
    if end_date:
        query = query.filter(AssetMarketData.trade_date <= end_date)

    data = query.order_by(AssetMarketData.trade_date.desc()).offset(skip).limit(limit).all()
    return data

@router.post("/market-data", response_model=AssetMarketDataResponse)
def create_market_data(data: AssetMarketDataCreate, db: Session = Depends(get_db)):
    """创建市场数据"""
    db_data = AssetMarketData(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data

# Screener Template endpoints
@router.get("/screener-templates", response_model=List[AssetScreenerTemplateResponse])
def get_screener_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    asset_type: Optional[str] = None,
    is_public: Optional[bool] = None,
    is_system: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取筛选器模板列表"""
    query = db.query(AssetScreenerTemplate)

    if asset_type:
        query = query.filter(AssetScreenerTemplate.asset_type == asset_type)
    if is_public is not None:
        query = query.filter(AssetScreenerTemplate.is_public == is_public)
    if is_system is not None:
        query = query.filter(AssetScreenerTemplate.is_system == is_system)

    templates = query.order_by(AssetScreenerTemplate.usage_count.desc()).offset(skip).limit(limit).all()
    return templates

@router.post("/screener-templates", response_model=AssetScreenerTemplateResponse)
def create_screener_template(template: AssetScreenerTemplateCreate, db: Session = Depends(get_db)):
    """创建筛选器模板"""
    db_template = AssetScreenerTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

# Backtest Template endpoints
@router.get("/backtest-templates", response_model=List[AssetBacktestTemplateResponse])
def get_backtest_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    asset_type: Optional[str] = None,
    strategy_type: Optional[str] = None,
    is_public: Optional[bool] = None,
    is_system: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取回测模板列表"""
    query = db.query(AssetBacktestTemplate)

    if asset_type:
        query = query.filter(AssetBacktestTemplate.asset_type == asset_type)
    if strategy_type:
        query = query.filter(AssetBacktestTemplate.strategy_type == strategy_type)
    if is_public is not None:
        query = query.filter(AssetBacktestTemplate.is_public == is_public)
    if is_system is not None:
        query = query.filter(AssetBacktestTemplate.is_system == is_system)

    templates = query.order_by(AssetBacktestTemplate.usage_count.desc()).offset(skip).limit(limit).all()
    return templates

@router.post("/backtest-templates", response_model=AssetBacktestTemplateResponse)
def create_backtest_template(template: AssetBacktestTemplateCreate, db: Session = Depends(get_db)):
    """创建回测模板"""
    db_template = AssetBacktestTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template
