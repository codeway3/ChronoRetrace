import asyncio
import logging
import warnings
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.api.v1 import a_industries as a_industries_v1
from app.api.v1 import admin as admin_v1
from app.api.v1 import backtest as backtest_v1
from app.api.v1 import commodities as commodities_v1
from app.api.v1 import crypto as crypto_v1
from app.api.v1 import data_quality as data_quality_v1
from app.api.v1 import futures as futures_v1
from app.api.v1 import options as options_v1
from app.api.v1 import screener as screener_v1
from app.api.v1 import stocks as stocks_v1
from app.core.config import settings
from app.infrastructure.database import models
from app.infrastructure.database.session import SessionLocal, engine
from app.data.fetchers import a_industries_fetcher

# Suppress the specific FutureWarning from baostock
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="The frame.append method is deprecated and will be removed from pandas in a future version. Use pandas.concat instead.",
    module="baostock.data.resultset",
)
# Suppress the warning from akshare about requests_html not being installed
warnings.filterwarnings("ignore", category=UserWarning, message="Certain functionality")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("yfinance").setLevel(
    logging.WARNING
)  # Quieten yfinance's debug messages
logging.getLogger("urllib3").setLevel(logging.INFO)  # Quieten urllib3's debug messages
logging.getLogger("apscheduler").setLevel(logging.WARNING)
# Ensure FastAPICache is initialized even in test/dev without Redis
try:
    # This will raise AssertionError if not initialized yet
    FastAPICache.get_backend()
except Exception:
    # Use in-memory backend as a safe default; lifespan will override with Redis later
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")


def create_db_and_tables():
    """
    Creates database tables and seeds initial data if necessary.
    """
    print("Creating database tables...")
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if the table is empty before seeding
        if db.query(models.StockInfo).count() == 0:
            print("Stock info table is empty. Seeding with default stocks...")
            # The DEFAULT_STOCKS list was removed from stocks.py, so this part is commented out.
            # If seeding is needed, it should be handled by a dedicated script or logic.
            # for stock in stocks_v1.DEFAULT_STOCKS:
            #     db_stock = models.StockInfo(ts_code=stock["ts_code"], name=stock["name"])
            #     db.add(db_stock)
            # db.commit()
            # print(f"{len(stocks_v1.DEFAULT_STOCKS)} default stocks seeded.")
            print("Default stock seeding is currently disabled.")
        else:
            print("Stock info table already contains data. Skipping seeding.")
    finally:
        db.close()


scheduler = AsyncIOScheduler()


async def warm_up_cache():
    """Pre-warms the cache for A-share industry overview for all windows."""
    print(
        "Warming up A-share industry overview cache for all windows (5D, 20D, 60D)..."
    )
    try:
        windows = ["5D", "20D", "60D"]
        # 顺序执行而不是并行执行，避免同时发送大量请求
        for window in windows:
            print(f"Warming up cache for window {window}...")

            # 记录连续失败的股票数量
            consecutive_failures = 0
            max_consecutive_failures = 10

            # 修改为直接调用build_overview，不使用重试逻辑
            try:
                # 获取行业列表
                if window == "5D":
                    industry_list = a_industries_fetcher.fetch_industry_list_em()
                else:
                    industry_list = a_industries_fetcher.fetch_industry_list_ths()

                if not industry_list:
                    print(f"Could not fetch industry list for window {window}")
                    continue

                days_map = {"5D": 5, "20D": 20, "60D": 60}
                days = days_map.get(window.upper(), 20)
                results = []

                # 限制处理的行业数量，避免一次性请求过多
                max_industries = 50
                if len(industry_list) > max_industries:
                    print(
                        f"Limiting to {max_industries} industries to avoid rate limiting"
                    )
                    industry_list = industry_list[:max_industries]

                import time

                for i, industry in enumerate(industry_list):
                    name = industry.get("industry_name")
                    code = industry.get("industry_code")
                    if not name or not code:
                        continue

                    # 每处理5个行业添加一个短暂延迟，避免请求过于频繁
                    if i > 0 and i % 5 == 0:
                        print(
                            f"Processed {i}/{len(industry_list)} industries, pausing briefly..."
                        )
                        time.sleep(2)

                    try:
                        # 获取行业历史数据，不使用重试逻辑
                        hist = a_industries_fetcher.fetch_industry_hist(name)

                        if hist.empty or len(hist) < 2:
                            print(
                                f"Not enough historical data for industry: {name} ({code})"
                            )
                            consecutive_failures += 1
                            if consecutive_failures >= max_consecutive_failures:
                                print(
                                    f"连续{max_consecutive_failures}只股票数据获取失败，中断拉取流程"
                                )
                                # 保存已获取的数据
                                if results:
                                    print(f"将已获取的{len(results)}条数据入库")
                                    # 这里可以添加数据入库的逻辑
                                break
                            continue

                        # 重置连续失败计数
                        consecutive_failures = 0

                        # 计算指标
                        last_row = hist.iloc[-1]
                        prev_row = hist.iloc[-2]

                        today_pct = (
                            (
                                (last_row["close"] - prev_row["close"])
                                / prev_row["close"]
                            )
                            * 100
                            if prev_row["close"] != 0
                            else 0
                        )
                        turnover = last_row.get("amount")

                        period_return = a_industries_fetcher.compute_period_return(
                            hist, days
                        )
                        sparkline_data = hist.tail(days)[["trade_date", "close"]].copy()
                        sparkline_data["close"] = sparkline_data["close"].astype(float)
                        sparkline = sparkline_data.to_dict(orient="records")

                        results.append(
                            {
                                "industry_code": code,
                                "industry_name": name,
                                "today_pct": float(today_pct),
                                "turnover": float(turnover)
                                if turnover is not None
                                else None,
                                "ret_window": period_return,
                                "window": window.upper(),
                                "sparkline": sparkline,
                            }
                        )
                    except Exception as exc:
                        print(f"Failed to process industry {name}: {exc}")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            print(
                                f"连续{max_consecutive_failures}只股票数据获取失败，中断拉取流程"
                            )
                            # 保存已获取的数据
                            if results:
                                print(f"将已获取的{len(results)}条数据入库")
                                # 这里可以添加数据入库的逻辑
                            break

                print(
                    f"Successfully built overview for {len(results)} industries for window {window}."
                )

            except Exception as e:
                print(f"An error occurred during processing window {window}: {e}")

            # 在每个窗口之间添加延迟，避免请求过于频繁
            await asyncio.sleep(5)

        print(
            "A-share industry overview cache is warmed up successfully for all windows."
        )
    except Exception as e:
        print(f"An error occurred during cache warm-up: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    print("Application startup...")
    create_db_and_tables()

    # Initialize FastAPI-Cache with Redis backend
    # IMPORTANT: fastapi-cache expects bytes from backend; set decode_responses=False
    # to avoid returning str and failing coder.decode(value.decode()).
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    print("FastAPI-Cache initialized with Redis.")

    # Schedule the cache warm-up job
    scheduler.add_job(warm_up_cache, "interval", hours=1, id="warm_up_cache_job")

    # Add stock metrics update job
    from app.jobs.update_daily_metrics import update_metrics_for_market

    async def update_stock_metrics():
        """更新股票指标的定时任务"""
        try:
            db = SessionLocal()
            try:
                a_share_count = await update_metrics_for_market(db, "A_share")
                us_stock_count = await update_metrics_for_market(db, "US_stock")
                total_count = a_share_count + us_stock_count
                print(f"Stock metrics update completed. Total updated: {total_count}")
            finally:
                db.close()
        except Exception as e:
            print(f"Failed to update stock metrics: {e}")

    # 每天下午6点执行（交易结束后）
    scheduler.add_job(
        update_stock_metrics, "cron", hour=18, minute=0, id="update_stock_metrics_job"
    )

    # 每6小时执行一次（避免过于频繁的请求）
    scheduler.add_job(
        update_stock_metrics,
        "interval",
        hours=6,
        id="update_stock_metrics_interval_job",
    )

    scheduler.start()
    # Run the warm-up immediately at startup
    await warm_up_cache()

    print("Application startup complete.")
    yield
    # On shutdown
    print("Application shutdown.")
    scheduler.shutdown()


app = FastAPI(
    title="ChronoRetrace API",
    description="API for the ChronoRetrace financial analysis tool.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows the React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(stocks_v1.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(admin_v1.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(
    backtest_v1.router, prefix="/api/v1/backtest", tags=["backtest"]
)  # Register the new backtest router
app.include_router(crypto_v1.router, prefix="/api/v1/crypto", tags=["crypto"])
app.include_router(
    commodities_v1.router, prefix="/api/v1/commodities", tags=["commodities"]
)
app.include_router(futures_v1.router, prefix="/api/v1/futures", tags=["futures"])
app.include_router(options_v1.router, prefix="/api/v1/options", tags=["options"])
app.include_router(
    a_industries_v1.router, prefix="/api/v1/a-industries", tags=["a-industries"]
)
app.include_router(screener_v1.router, prefix="/api/v1", tags=["screener"])
app.include_router(
    data_quality_v1.router, prefix="/api/v1/data-quality", tags=["data-quality"]
)


@app.get("/")
def read_root():
    return {"message": "Welcome to ChronoRetrace API"}
