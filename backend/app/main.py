import asyncio
import logging
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

from app.api.v1 import a_industries as a_industries_v1
from app.api.v1 import admin as admin_v1
from app.api.v1 import asset_backtest as asset_backtest_v1
from app.api.v1 import asset_screener as asset_screener_v1
from app.api.v1 import auth as auth_v1
from app.api.v1 import backtest as backtest_v1
from app.api.v1 import cache as cache_v1
from app.api.v1 import cached_stocks as cached_stocks_v1
from app.api.v1 import commodities as commodities_v1
from app.api.v1 import crypto as crypto_v1
from app.api.v1 import data_quality as data_quality_v1
from app.api.v1 import futures as futures_v1
from app.api.v1 import health as health_v1
from app.api.v1 import monitoring as monitoring_v1
from app.api.v1 import options as options_v1
from app.api.v1 import screener as screener_v1
from app.api.v1 import stocks as stocks_v1
from app.api.v1 import users as users_v1
from app.api.v1 import watchlist as watchlist_v1
from app.api.v1 import websocket as websocket_v1
from app.core.config import settings
from app.core.middleware import setup_middleware

# Logger is already configured above with logging.basicConfig
from app.data.fetchers import a_industries_fetcher
from app.infrastructure.cache.cache_warming import cache_warming_service
from app.infrastructure.database import models
from app.infrastructure.database.init_db import initialize_database
from app.infrastructure.database.session import SessionLocal, engine
from app.infrastructure.monitoring import performance_monitor
from app.infrastructure.monitoring.middleware import (
    CacheMonitoringMiddleware,
    PerformanceMonitoringMiddleware,
)

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
logger = logging.getLogger(__name__)
logging.getLogger("yfinance").setLevel(
    logging.WARNING
)  # Quieten yfinance's debug messages
logging.getLogger("urllib3").setLevel(logging.INFO)  # Quieten urllib3's debug messages
logging.getLogger("apscheduler").setLevel(logging.WARNING)
# Enable debug logging for cache warming
logging.getLogger("app.infrastructure.cache.cache_warming").setLevel(logging.DEBUG)
# FastAPICache will be initialized in lifespan function with Redis backend


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

# Redis键名用于存储上次行业数据预热时间
INDUSTRY_WARMING_TIME_KEY = "industry_warming:last_time"
INDUSTRY_WARMING_TIME_FILE = Path("cache_warming_time.txt")


async def warm_up_cache():
    """Pre-warms the cache for A-share industry overview for all windows."""
    print("=== WARM_UP_CACHE FUNCTION CALLED ===")
    print("Cache warm-up function called...")

    # 从Redis获取上次预热时间
    try:
        print("Attempting to get Redis backend...")
        backend = FastAPICache.get_backend()
        print(f"Redis backend obtained: {backend}")

        print(
            f"Attempting to get last warming time with key: {INDUSTRY_WARMING_TIME_KEY}"
        )
        last_warming_str = await backend.get(INDUSTRY_WARMING_TIME_KEY)
        print(f"Retrieved last warming time from Redis: {last_warming_str}")

        if last_warming_str:
            print("Found previous warming time, parsing...")
            last_warming_time = datetime.fromisoformat(last_warming_str.decode("utf-8"))
            time_since_last_warming = datetime.now() - last_warming_time
            print(f"Last warming time: {last_warming_time}")
            print(f"Time since last warming: {time_since_last_warming}")
            print(f"12 hour threshold: {timedelta(hours=12)}")

            if time_since_last_warming < timedelta(hours=12):
                remaining_time = timedelta(hours=12) - time_since_last_warming
                print(
                    f"距离上次行业数据预热不足12小时，跳过预热。剩余等待时间: {remaining_time}"
                )
                print("=== RETURNING EARLY DUE TO TIME CONSTRAINT ===")
                return
            else:
                print("距离上次预热已超过12小时，开始新的预热")
        else:
            print("未找到上次预热时间记录，开始首次预热")
    except Exception as e:
        print(f"获取上次预热时间失败，继续执行预热: {e}")
        import traceback

        traceback.print_exc()

    print("=== PROCEEDING WITH CACHE WARMING ===")

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
                results: list[dict] = []

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
                                "turnover": (
                                    float(turnover) if turnover is not None else None
                                ),
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

        # 保存预热时间到Redis
        try:
            backend = FastAPICache.get_backend()
            current_time = datetime.now()
            await backend.set(
                INDUSTRY_WARMING_TIME_KEY, current_time.isoformat().encode("utf-8")
            )
            print(
                f"行业数据预热完成，下次预热时间: {current_time + timedelta(hours=12)}"
            )
        except Exception as e:
            print(f"保存预热时间失败: {e}")

    except Exception as e:
        print(f"An error occurred during cache warm-up: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("正在启动应用...")

    # 初始化数据库
    try:
        success = initialize_database()
        if success:
            logger.info("✅ 数据库初始化成功")
        else:
            logger.error("❌ 数据库初始化失败")
            raise Exception("数据库初始化失败")
    except Exception as e:
        logger.error(f"启动时数据库初始化出错: {e}")
        raise

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
    # 同步运行预热（会检查时间间隔限制）
    try:
        # 使用 asyncio.create_task 创建任务但不等待，使其在后台运行
        asyncio.create_task(warm_up_cache())
        print("行业数据预热任务已启动（后台运行）")
    except Exception as e:
        print(f"启动预热任务出错: {e}")
        # 继续启动，不因预热失败而中断整个应用

    # Run comprehensive cache warming
    print("Starting comprehensive cache warming...")
    warming_result = await cache_warming_service.warm_all_caches(force=True)
    print(f"Cache warming completed: {warming_result.get('status', 'unknown')}")
    print(f"Cache warming stats: {warming_result.get('stats', {})}")
    print(
        f"Total keys warmed: {warming_result.get('stats', {}).get('stock_list', 0) + warming_result.get('stats', {}).get('hot_stocks_data', 0) + warming_result.get('stats', {}).get('market_metrics', 0) + warming_result.get('stats', {}).get('fundamental_data', 0)}"
    )

    # Initialize performance monitor
    performance_monitor.start_monitoring()
    print("Performance monitoring started.")

    # Initialize WebSocket services
    try:
        from app.websocket.connection_manager import ConnectionManager
        from app.websocket.data_stream_service import DataStreamService
        from app.infrastructure.cache.redis_manager import RedisCacheManager
        from app.api.v1.websocket import init_websocket_services

        logger.info("正在初始化WebSocket服务...")

        connection_manager = ConnectionManager()
        redis_manager = RedisCacheManager()
        data_stream_service = DataStreamService(connection_manager, redis_manager)

        # Store services in app state for access in routes
        app.state.connection_manager = connection_manager
        app.state.data_stream_service = data_stream_service

        # Initialize WebSocket services in the router
        init_websocket_services(redis_manager)

        # Start data stream service
        await data_stream_service.start()
        logger.info("✅ WebSocket服务初始化并启动成功")

    except Exception as e:
        logger.error(f"❌ WebSocket服务初始化失败: {e}")
        # 不抛出异常，允许应用继续启动（WebSocket功能可能不可用）
        app.state.connection_manager = None
        app.state.data_stream_service = None

    logger.info("✅ 应用启动完成")
    yield
    # On shutdown
    logger.info("正在关闭应用...")

    # Stop WebSocket services
    try:
        if hasattr(app.state, "data_stream_service") and app.state.data_stream_service:
            await app.state.data_stream_service.stop()
            logger.info("✅ WebSocket服务已停止")
    except Exception as e:
        logger.error(f"停止WebSocket服务时出错: {e}")

    performance_monitor.stop_monitoring()
    scheduler.shutdown()
    logger.info("✅ 应用已关闭")


app = FastAPI(
    title="ChronoRetrace API",
    description="API for the ChronoRetrace financial analysis tool.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS.split(","),
    allow_headers=(
        settings.CORS_ALLOW_HEADERS.split(",")
        if settings.CORS_ALLOW_HEADERS != "*"
        else ["*"]
    ),
)

# Add monitoring middleware
app.add_middleware(
    PerformanceMonitoringMiddleware,
    exclude_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"],
)
app.add_middleware(CacheMonitoringMiddleware)

# 设置中间件
setup_middleware(app)

# 数据库初始化已迁移到lifespan函数中

# Include API routers
app.include_router(auth_v1.router, prefix="/api/v1", tags=["auth"])
app.include_router(users_v1.router, prefix="/api/v1", tags=["users"])
app.include_router(watchlist_v1.router, prefix="/api/v1/watchlist", tags=["watchlist"])
app.include_router(stocks_v1.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(
    cached_stocks_v1.router, prefix="/api/v1/cached-stocks", tags=["cached-stocks"]
)
app.include_router(monitoring_v1.router, prefix="/api/v1", tags=["monitoring"])
app.include_router(cache_v1.router, prefix="/api/v1", tags=["cache"])
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
    asset_screener_v1.router, prefix="/api/v1/assets", tags=["asset-screener"]
)
app.include_router(
    asset_backtest_v1.router, prefix="/api/v1/assets", tags=["asset-backtest"]
)
app.include_router(
    data_quality_v1.router, prefix="/api/v1/data-quality", tags=["data-quality"]
)
app.include_router(health_v1.router, prefix="/api/v1/health", tags=["health"])

# Register WebSocket router
app.include_router(websocket_v1.router, prefix="/api/v1/ws", tags=["websocket"])

# Register asset config router
from app.api.v1 import asset_config as asset_config_v1

app.include_router(
    asset_config_v1.router, prefix="/api/v1/asset-config", tags=["asset-config"]
)


@app.get("/")
def read_root():
    return {"message": "Welcome to ChronoRetrace API"}


@app.get("/health")
def health_check():
    """简单的健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
