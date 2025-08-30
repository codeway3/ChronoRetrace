#!/usr/bin/env python3
"""
手动执行股票指标更新脚本
用于手动触发股票数据更新，包含更好的错误处理和频率限制
"""

import asyncio
import logging
from datetime import date
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import StockInfo, DailyStockMetrics
from app.services.a_share_fetcher import fetch_a_share_data_from_akshare, _fetch_spot_data_batch
from app.services.us_stock_fetcher import fetch_from_yfinance, fetch_us_fundamental_data_from_yfinance
import pandas as pd
from datetime import timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def calculate_technical_metrics(df: pd.DataFrame):
    """计算技术指标"""
    try:
        if df is None or df.empty or len(df) < 20:
            return None
        
        # 计算移动平均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        latest = df.iloc[-1]
        close_price = float(latest['close']) if pd.notna(latest['close']) else None
        volume_val = int(latest['vol']) if pd.notna(latest['vol']) else None
        
        return {
            "close_price": close_price,
            "ma5": float(latest['ma5']) if pd.notna(latest['ma5']) else None,
            "ma20": float(latest['ma20']) if pd.notna(latest['ma20']) else None,
            "volume": volume_val,
        }
    except Exception as e:
        logger.error(f"Error calculating technical metrics: {e}")
        return None


async def update_a_share_metrics_safe(db: Session, max_stocks: int = 100) -> int:
    """安全地更新A股指标，限制处理数量避免频率限制"""
    logger.info(f"Starting A-share metrics update (max {max_stocks} stocks)")
    
    # 获取A股列表，限制数量
    stocks = db.query(StockInfo).filter(StockInfo.market_type == 'A_share').limit(max_stocks).all()
    logger.info(f"Found {len(stocks)} A-share stocks to process")
    
    updated_count = 0
    failed_count = 0
    max_failures = 10  # 最大连续失败数
    
    try:
        # 尝试批量获取
        logger.info("Attempting batch fetch for A-share data...")
        batch_data = await asyncio.to_thread(_fetch_spot_data_batch)
        
        if batch_data and isinstance(batch_data, dict):
            logger.info(f"Batch fetch successful, got data for {len(batch_data)} instruments")
            
            for i, stock in enumerate(stocks):
                try:
                    if stock.ts_code in batch_data:
                        stock_df = batch_data[stock.ts_code]
                        if stock_df is not None and not stock_df.empty:
                            row = stock_df.iloc[0]
                            metrics_data = {
                                "code": stock.ts_code,
                                "market": "A_share",
                                "date": date.today(),
                                "close_price": float(row.get('close')) if pd.notna(row.get('close')) else None,
                                "volume": int(row.get('vol')) if pd.notna(row.get('vol')) else None,
                                "pe_ratio": float(row.get('pe_ratio')) if pd.notna(row.get('pe_ratio')) else None,
                                "pb_ratio": float(row.get('pb_ratio')) if pd.notna(row.get('pb_ratio')) else None,
                                "market_cap": int(row.get('market_cap')) if pd.notna(row.get('market_cap')) else None,
                            }
                            
                            # 更新数据库
                            existing = db.query(DailyStockMetrics).filter(
                                DailyStockMetrics.code == stock.ts_code,
                                DailyStockMetrics.date == date.today(),
                                DailyStockMetrics.market == "A_share"
                            ).first()
                            
                            if existing:
                                for key, value in metrics_data.items():
                                    if value is not None:
                                        setattr(existing, key, value)
                            else:
                                new_metrics = DailyStockMetrics(**metrics_data)
                                db.add(new_metrics)
                            
                            updated_count += 1
                            failed_count = 0  # 重置失败计数
                            
                            if updated_count % 50 == 0:
                                db.commit()
                                logger.info(f"Processed {updated_count}/{len(stocks)} stocks")
                        else:
                            failed_count += 1
                            logger.warning(f"Empty data for {stock.ts_code}")
                    else:
                        failed_count += 1
                        logger.warning(f"No batch data for {stock.ts_code}")
                    
                    # 检查连续失败
                    if failed_count >= max_failures:
                        logger.warning(f"Too many consecutive failures ({failed_count}), stopping update")
                        break
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to process {stock.ts_code}: {e}")
                    if failed_count >= max_failures:
                        logger.warning(f"Too many consecutive failures ({failed_count}), stopping update")
                        break
        else:
            logger.warning("Batch fetch failed, falling back to individual fetch")
            # 回退到逐个获取，但限制数量
            for i, stock in enumerate(stocks[:50]):  # 只处理前50只股票
                try:
                    df = await asyncio.to_thread(
                        fetch_a_share_data_from_akshare,
                        stock_code=stock.ts_code,
                        interval='daily'
                    )
                    
                    if df is None or df.empty:
                        failed_count += 1
                        logger.warning(f"No data for {stock.ts_code}")
                        if failed_count >= max_failures:
                            break
                        continue
                    
                    last = df.iloc[-1]
                    metrics_data = {
                        "code": stock.ts_code,
                        "market": "A_share",
                        "date": date.today(),
                        "close_price": float(last['close']) if pd.notna(last['close']) else None,
                        "volume": int(last['vol']) if pd.notna(last['vol']) else None,
                    }
                    
                    existing = db.query(DailyStockMetrics).filter(
                        DailyStockMetrics.code == stock.ts_code,
                        DailyStockMetrics.date == date.today(),
                        DailyStockMetrics.market == "A_share"
                    ).first()
                    
                    if existing:
                        for key, value in metrics_data.items():
                            if value is not None:
                                setattr(existing, key, value)
                    else:
                        new_metrics = DailyStockMetrics(**metrics_data)
                        db.add(new_metrics)
                    
                    updated_count += 1
                    failed_count = 0
                    
                    if updated_count % 20 == 0:
                        db.commit()
                        logger.info(f"Processed {updated_count} stocks")
                        # 添加延迟避免频率限制
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to process {stock.ts_code}: {e}")
                    if failed_count >= max_failures:
                        logger.warning("Too many consecutive failures, stopping")
                        break
                    await asyncio.sleep(1)  # 失败后短暂延迟
    
    except Exception as e:
        logger.error(f"A-share update failed: {e}")
    
    finally:
        db.commit()
        logger.info(f"A-share update completed: {updated_count} stocks updated, {failed_count} failures")
    
    return updated_count


async def update_us_stock_metrics_safe(db: Session, max_stocks: int = 50) -> int:
    """安全地更新美股指标，限制处理数量"""
    logger.info(f"Starting US stock metrics update (max {max_stocks} stocks)")
    
    stocks = db.query(StockInfo).filter(StockInfo.market_type == 'US_stock').limit(max_stocks).all()
    logger.info(f"Found {len(stocks)} US stocks to process")
    
    updated_count = 0
    failed_count = 0
    max_failures = 5
    
    for stock in stocks:
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=60)
            
            df = await asyncio.to_thread(
                fetch_from_yfinance,
                ts_code=stock.ts_code,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                interval='daily'
            )
            
            if df is None or df.empty:
                failed_count += 1
                logger.warning(f"No data for {stock.ts_code}")
                if failed_count >= max_failures:
                    break
                continue
            
            fundamentals = await asyncio.to_thread(
                fetch_us_fundamental_data_from_yfinance,
                stock.ts_code
            )
            
            tech_metrics = calculate_technical_metrics(df)
            if not tech_metrics:
                failed_count += 1
                continue
            
            metrics_data = {
                "code": stock.ts_code,
                "market": "US_stock",
                "date": end_date,
                **tech_metrics,
                "pe_ratio": fundamentals.get('pe_ratio'),
                "pb_ratio": fundamentals.get('pb_ratio'),
                "market_cap": fundamentals.get('market_cap'),
                "dividend_yield": fundamentals.get('dividend_yield'),
            }
            
            existing = db.query(DailyStockMetrics).filter(
                DailyStockMetrics.code == stock.ts_code,
                DailyStockMetrics.date == end_date,
                DailyStockMetrics.market == "US_stock"
            ).first()
            
            if existing:
                for key, value in metrics_data.items():
                    if value is not None:
                        setattr(existing, key, value)
            else:
                new_metrics = DailyStockMetrics(**metrics_data)
                db.add(new_metrics)
            
            updated_count += 1
            failed_count = 0
            
            if updated_count % 10 == 0:
                db.commit()
                logger.info(f"Processed {updated_count} US stocks")
                await asyncio.sleep(1)  # 避免频率限制
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to process {stock.ts_code}: {e}")
            if failed_count >= max_failures:
                logger.warning("Too many failures, stopping US stock update")
                break
            await asyncio.sleep(0.5)
    
    db.commit()
    logger.info(f"US stock update completed: {updated_count} stocks updated")
    return updated_count


async def main():
    """主函数"""
    logger.info("Starting manual stock metrics update")
    
    db = SessionLocal()
    try:
        # 更新A股数据（限制数量）
        a_share_count = await update_a_share_metrics_safe(db, max_stocks=100)
        
        # 短暂延迟
        await asyncio.sleep(5)
        
        # 更新美股数据（限制数量）
        us_stock_count = await update_us_stock_metrics_safe(db, max_stocks=50)
        
        total_count = a_share_count + us_stock_count
        logger.info(f"Manual update completed. Total updated: {total_count} stocks")
        
    except Exception as e:
        logger.error(f"Manual update failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())