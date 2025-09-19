from typing import Union

# !/usr/bin/env python3
"""
股票指标数据更新任务
每天自动更新所有股票的技术指标和基本面数据，用于股票筛选器功能
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.data.fetchers.stock_fetchers.a_share_fetcher import (
    _fetch_spot_data_batch,
    fetch_a_share_data_from_akshare,
)
from app.data.fetchers.stock_fetchers.us_stock_fetcher import (
    fetch_from_yfinance,
    fetch_us_fundamental_data_from_yfinance,
)
from app.infrastructure.database.models import DailyStockMetrics, StockInfo
from app.infrastructure.database.session import SessionLocal

logger = logging.getLogger(__name__)


def calculate_technical_metrics(df: pd.DataFrame) -> Union[dict[str, Any], None]:
    """计算技术指标

    约定：
    - 少于20条记录时返回 None（与测试期望一致）
    - 返回字段：close_price, ma5, ma20, volume（不返回 ma10）
    - 支持日期列为 trade_date 或 date
    """
    if df is None or df.empty or len(df) < 20:
        return None

    try:
        # 统一日期列并按时间升序
        date_col = (
            "trade_date"
            if "trade_date" in df.columns
            else ("date" if "date" in df.columns else None)
        )
        if date_col:
            df = df.sort_values(by=date_col)

        # 计算移动平均线
        df["ma5"] = df["close"].rolling(window=5).mean()
        df["ma20"] = df["close"].rolling(window=20).mean()

        latest = df.iloc[-1]
        close_price = float(latest["close"]) if pd.notna(latest["close"]) else None
        volume_val = int(latest["vol"]) if pd.notna(latest["vol"]) else None

        return {
            "close_price": close_price,
            "ma5": float(latest["ma5"]) if pd.notna(latest["ma5"]) else None,
            "ma20": float(latest["ma20"]) if pd.notna(latest["ma20"]) else None,
            "volume": volume_val,
        }
    except Exception as e:
        logger.error(f"Error calculating technical metrics: {e}")
        return None


async def fetch_a_share_fundamentals(stock_code: str) -> dict[str, Any]:
    """获取A股基本面数据"""
    try:
        # 使用 akshare 获取基本面数据
        # 这里需要根据实际的 akshare API 来实现
        # 暂时返回空数据，后续可以扩展
        logger.info(f"Fetching A-share fundamentals for {stock_code}")

        # TODO: 实现实际的 akshare 基本面数据获取
        # 可以使用以下API：
        # - ak.stock_individual_info_em() 获取基本信息
        # - ak.stock_zh_a_spot_em() 获取实时行情（包含PE、PB等）

        return {
            "pe_ratio": None,
            "pb_ratio": None,
            "market_cap": None,
            "dividend_yield": None,
        }
    except Exception as e:
        logger.error(f"Failed to fetch A-share fundamentals for {stock_code}: {e}")
        return {}


async def update_metrics_for_market(db: Session, market: str) -> int:
    """更新指定市场的股票指标"""
    logger.info(f"Starting metrics update for {market}")

    # 获取该市场的所有股票
    stocks = db.query(StockInfo).filter(StockInfo.market_type == market).all()
    logger.info(f"Found {len(stocks)} stocks for {market}")

    updated_count = 0
    failed_count = 0
    consecutive_failures = 0
    max_consecutive_failures = 10  # 连续失败10次就熔断
    max_total_failures = min(
        50, len(stocks) // 10
    )  # 总失败数不超过50次或股票总数的1/10

    if market == "A_share":
        # 使用批量获取接口
        try:
            logger.info("Using batch fetch for A-share data to avoid frequency limits")
            batch_data = await asyncio.to_thread(_fetch_spot_data_batch)

            if batch_data:
                if not isinstance(batch_data, dict):
                    raise TypeError(
                        "Malformed batch spot data: expected dict[ts_code -> DataFrame]"
                    )
                logger.info(
                    f"Successfully fetched batch data for {len(batch_data)} instruments"
                )

                for stock in stocks:
                    try:
                        # 检查是否应该停止处理
                        if consecutive_failures >= max_consecutive_failures:
                            logger.warning(
                                f"Too many consecutive failures ({consecutive_failures}), stopping A-share update"
                            )
                            break
                        if failed_count >= max_total_failures:
                            logger.warning(
                                f"Too many total failures ({failed_count}), stopping A-share update"
                            )
                            break

                        if stock.ts_code in batch_data:
                            stock_df = batch_data[stock.ts_code]
                            if stock_df is None or stock_df.empty:
                                logger.warning(f"Empty batch row for {stock.ts_code}")
                                failed_count += 1
                                consecutive_failures += 1
                                # 逐标的回退
                                fallback_df = await asyncio.to_thread(
                                    fetch_a_share_data_from_akshare,
                                    stock_code=stock.ts_code,
                                    interval="daily",
                                )
                                if fallback_df is None or fallback_df.empty:
                                    continue
                                last = fallback_df.iloc[-1]
                                metrics_data = {
                                    "code": stock.ts_code,
                                    "market": market,
                                    "date": date.today(),
                                    "close_price": (
                                        float(last["close"])
                                        if pd.notna(last["close"])
                                        else None
                                    ),
                                    "volume": (
                                        int(last["vol"])
                                        if pd.notna(last["vol"])
                                        else None
                                    ),
                                }
                                consecutive_failures = 0  # 重置连续失败计数
                            else:
                                row = stock_df.iloc[0]
                                metrics_data = {
                                    "code": stock.ts_code,
                                    "market": market,
                                    "date": date.today(),
                                    "close_price": (
                                        float(row.get("close"))
                                        if pd.notna(row.get("close"))
                                        else None
                                    ),
                                    "volume": (
                                        int(row.get("vol"))
                                        if pd.notna(row.get("vol"))
                                        else None
                                    ),
                                    "pe_ratio": (
                                        float(row.get("pe_ratio"))
                                        if pd.notna(row.get("pe_ratio"))
                                        else None
                                    ),
                                    "pb_ratio": (
                                        float(row.get("pb_ratio"))
                                        if pd.notna(row.get("pb_ratio"))
                                        else None
                                    ),
                                    "market_cap": (
                                        int(row.get("market_cap"))
                                        if pd.notna(row.get("market_cap"))
                                        else None
                                    ),
                                }
                                consecutive_failures = 0  # 重置连续失败计数

                            # 更新数据库
                            existing = (
                                db.query(DailyStockMetrics)
                                .filter(
                                    DailyStockMetrics.code == stock.ts_code,
                                    DailyStockMetrics.date == date.today(),
                                    DailyStockMetrics.market == market,
                                )
                                .first()
                            )

                            if existing:
                                for key, value in metrics_data.items():
                                    if value is not None:
                                        setattr(existing, key, value)
                                logger.debug(
                                    f"Updated existing metrics for {stock.ts_code}"
                                )
                            else:
                                new_metrics = DailyStockMetrics(**metrics_data)
                                db.add(new_metrics)
                                logger.debug(f"Created new metrics for {stock.ts_code}")

                            updated_count += 1
                            if updated_count % 100 == 0:
                                db.commit()
                                logger.info(
                                    f"Processed {updated_count}/{len(stocks)} stocks for {market}"
                                )
                        else:
                            failed_count += 1
                            consecutive_failures += 1
                            # 逐标的回退
                            fallback_df = await asyncio.to_thread(
                                fetch_a_share_data_from_akshare,
                                stock_code=stock.ts_code,
                                interval="daily",
                            )
                            if fallback_df is None or fallback_df.empty:
                                logger.warning(f"No data available for {stock.ts_code}")
                                # 检查是否应该停止处理
                                if consecutive_failures >= max_consecutive_failures:
                                    logger.warning(
                                        f"Too many consecutive failures ({consecutive_failures}), stopping A-share update"
                                    )
                                    break
                                if failed_count >= max_total_failures:
                                    logger.warning(
                                        f"Too many total failures ({failed_count}), stopping A-share update"
                                    )
                                    break
                                continue
                            last = fallback_df.iloc[-1]
                            metrics_data = {
                                "code": stock.ts_code,
                                "market": market,
                                "date": date.today(),
                                "close_price": (
                                    float(last["close"])
                                    if pd.notna(last["close"])
                                    else None
                                ),
                                "volume": (
                                    int(last["vol"]) if pd.notna(last["vol"]) else None
                                ),
                            }
                            consecutive_failures = 0  # 重置连续失败计数

                            existing = (
                                db.query(DailyStockMetrics)
                                .filter(
                                    DailyStockMetrics.code == stock.ts_code,
                                    DailyStockMetrics.date == date.today(),
                                    DailyStockMetrics.market == market,
                                )
                                .first()
                            )
                            if existing:
                                for key, value in metrics_data.items():
                                    if value is not None:
                                        setattr(existing, key, value)
                                logger.debug(
                                    f"Updated existing metrics for {stock.ts_code}"
                                )
                            else:
                                new_metrics = DailyStockMetrics(**metrics_data)
                                db.add(new_metrics)
                                logger.debug(f"Created new metrics for {stock.ts_code}")
                            updated_count += 1
                            if updated_count % 100 == 0:
                                db.commit()
                                logger.info(
                                    f"Processed {updated_count}/{len(stocks)} stocks for {market}"
                                )

                    except Exception as e:
                        failed_count += 1
                        consecutive_failures += 1
                        logger.error(f"Failed to update {stock.ts_code}: {e}")
                        # 检查是否应该停止处理
                        if consecutive_failures >= max_consecutive_failures:
                            logger.warning(
                                f"Too many consecutive failures ({consecutive_failures}), stopping A-share update"
                            )
                            break
                        if failed_count >= max_total_failures:
                            logger.warning(
                                f"Too many total failures ({failed_count}), stopping A-share update"
                            )
                            break
                        continue

        except Exception as e:
            logger.error(f"Batch fetch failed, falling back to individual fetch: {e}")
            # 全量回退为逐个获取
            # 不重置失败计数器，保持熔断机制有效

            for stock in stocks:
                try:
                    end_date = date.today()
                    df = await asyncio.to_thread(
                        fetch_a_share_data_from_akshare,
                        stock_code=stock.ts_code,
                        interval="daily",
                    )
                    if df is None or df.empty:
                        failed_count += 1
                        consecutive_failures += 1
                        logger.warning(f"No data available for {stock.ts_code}")
                        # 检查是否应该停止处理
                        if consecutive_failures >= max_consecutive_failures:
                            logger.warning(
                                f"Too many consecutive failures ({consecutive_failures}), stopping A-share fallback update"
                            )
                            break
                        if failed_count >= max_total_failures:
                            logger.warning(
                                f"Too many total failures ({failed_count}), stopping A-share fallback update"
                            )
                            break
                        continue
                    last = df.iloc[-1]
                    metrics_data = {
                        "code": stock.ts_code,
                        "market": market,
                        "date": end_date,
                        "close_price": (
                            float(last["close"]) if pd.notna(last["close"]) else None
                        ),
                        "volume": int(last["vol"]) if pd.notna(last["vol"]) else None,
                    }
                    existing = (
                        db.query(DailyStockMetrics)
                        .filter(
                            DailyStockMetrics.code == stock.ts_code,
                            DailyStockMetrics.date == end_date,
                            DailyStockMetrics.market == market,
                        )
                        .first()
                    )
                    if existing:
                        for key, value in metrics_data.items():
                            if value is not None:
                                setattr(existing, key, value)
                        logger.debug(f"Updated existing metrics for {stock.ts_code}")
                    else:
                        new_metrics = DailyStockMetrics(**metrics_data)
                        db.add(new_metrics)
                        logger.debug(f"Created new metrics for {stock.ts_code}")
                    updated_count += 1
                    consecutive_failures = 0  # 重置连续失败计数
                    if updated_count % 100 == 0:
                        db.commit()
                        logger.info(
                            f"Processed {updated_count}/{len(stocks)} stocks for {market}"
                        )
                except Exception as e:
                    failed_count += 1
                    consecutive_failures += 1
                    logger.error(f"Failed to update {stock.ts_code}: {e}")

                    # 检查是否应该停止处理
                    if consecutive_failures >= max_consecutive_failures:
                        logger.warning(
                            f"Too many consecutive failures ({consecutive_failures}), stopping A-share fallback update"
                        )
                        break
                    if failed_count >= max_total_failures:
                        logger.warning(
                            f"Too many total failures ({failed_count}), stopping A-share fallback update"
                        )
                        break
                    continue

    elif market == "US_stock":
        # 美股使用原有的逐个获取方法
        # 重置失败计数器
        failed_count = 0
        consecutive_failures = 0
        max_consecutive_failures = 15
        max_total_failures = len(stocks) // 4  # 最多失败1/4的股票

        for stock in stocks:
            try:
                # 1. 获取K线数据
                end_date = date.today()
                start_date = end_date - timedelta(days=60)

                df = await asyncio.to_thread(
                    fetch_from_yfinance,
                    ts_code=stock.ts_code,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    interval="daily",
                )
                fundamentals = await asyncio.to_thread(
                    fetch_us_fundamental_data_from_yfinance, stock.ts_code
                )

                if df is None or df.empty:
                    logger.warning(f"No data available for {stock.ts_code}")
                    continue

                # 2. 计算技术指标
                tech_metrics = calculate_technical_metrics(df)
                if not tech_metrics:
                    logger.warning(
                        f"Failed to calculate technical metrics for {stock.ts_code}"
                    )
                    continue

                # 3. 准备最终数据
                # 安全处理 fundamentals 可能为 None 的情况
                fund_data = fundamentals or {}

                metrics_data = {
                    "code": stock.ts_code,
                    "market": market,
                    "date": end_date,
                    **tech_metrics,
                    "pe_ratio": fund_data.get("pe_ratio"),
                    "pb_ratio": fund_data.get("pb_ratio"),
                    "market_cap": fund_data.get("market_cap"),
                    "dividend_yield": fund_data.get("dividend_yield"),
                }

                # 4. 更新数据库
                existing = (
                    db.query(DailyStockMetrics)
                    .filter(
                        DailyStockMetrics.code == stock.ts_code,
                        DailyStockMetrics.date == end_date,
                        DailyStockMetrics.market == market,
                    )
                    .first()
                )

                if existing:
                    # 更新现有记录
                    for key, value in metrics_data.items():
                        if value is not None:
                            setattr(existing, key, value)
                    logger.debug(f"Updated existing metrics for {stock.ts_code}")
                else:
                    # 创建新记录
                    new_metrics = DailyStockMetrics(**metrics_data)
                    db.add(new_metrics)
                    logger.debug(f"Created new metrics for {stock.ts_code}")

                updated_count += 1
                consecutive_failures = 0  # 重置连续失败计数

                # 每处理100只股票提交一次，避免事务过大
                if updated_count % 100 == 0:
                    db.commit()
                    logger.info(
                        f"Processed {updated_count}/{len(stocks)} stocks for {market}"
                    )

            except Exception as e:
                failed_count += 1
                consecutive_failures += 1
                logger.error(f"Failed to update {stock.ts_code}: {e}")

                # 检查是否应该停止处理
                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(
                        f"Too many consecutive failures ({consecutive_failures}), stopping US stock update"
                    )
                    break
                if failed_count >= max_total_failures:
                    logger.warning(
                        f"Too many total failures ({failed_count}), stopping US stock update"
                    )
                    break
                continue

    # 提交剩余的更改
    db.commit()
    logger.info(f"Successfully updated {updated_count} stocks for {market}")
    return updated_count


async def main():
    """主函数"""
    logger.info("Starting the daily stock metrics update job")
    db = SessionLocal()
    try:
        # 更新A股数据
        a_share_count = await update_metrics_for_market(db, "A_share")
        logger.info(f"A-share metrics update completed: {a_share_count} stocks updated")

        # 更新美股数据
        us_stock_count = await update_metrics_for_market(db, "US_stock")
        logger.info(
            f"US stock metrics update completed: {us_stock_count} stocks updated"
        )

        logger.info("Daily stock metrics update job completed successfully")

    except Exception as e:
        logger.error(f"Daily stock metrics update job failed: {e}", exc_info=True)
        raise
    finally:
        db.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
        logger.info("Script execution completed")
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"Script failed: {e}")
    finally:
        logger.info("Exiting script")
        import sys

        sys.exit(0)
