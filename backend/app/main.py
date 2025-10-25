import asyncio
import logging
import os
import traceback
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

from app.analytics.api import endpoints as analytics_endpoints
from app.api.v1 import (
    a_industries as a_industries_v1,
)
from app.api.v1 import (
    admin as admin_v1,
)
from app.api.v1 import (
    asset_backtest as asset_backtest_v1,
)
from app.api.v1 import (
    asset_config as asset_config_v1,
)
from app.api.v1 import (
    asset_screener as asset_screener_v1,
)
from app.api.v1 import (
    auth as auth_v1,
)
from app.api.v1 import (
    backtest as backtest_v1,
)
from app.api.v1 import (
    cache as cache_v1,
)
from app.api.v1 import (
    cached_stocks as cached_stocks_v1,
)
from app.api.v1 import (
    commodities as commodities_v1,
)
from app.api.v1 import (
    crypto as crypto_v1,
)
from app.api.v1 import (
    data_quality as data_quality_v1,
)
from app.api.v1 import (
    futures as futures_v1,
)
from app.api.v1 import (
    health as health_v1,
)
from app.api.v1 import (
    monitoring as monitoring_v1,
)
from app.api.v1 import (
    options as options_v1,
)
from app.api.v1 import (
    screener as screener_v1,
)
from app.api.v1 import (
    stocks as stocks_v1,
)
from app.api.v1 import (
    users as users_v1,
)
from app.api.v1 import (
    watchlist as watchlist_v1,
)
from app.api.v1 import (
    websocket as websocket_v1,
)
from app.api.v1.websocket import init_websocket_services
from app.core.config import settings
from app.core.middleware import setup_middleware

# Logger is already configured above with logging.basicConfig
from app.data.fetchers import a_industries_fetcher
from app.infrastructure.cache.cache_warming import cache_warming_service
from app.infrastructure.cache.redis_manager import RedisCacheManager
from app.infrastructure.database import models
from app.infrastructure.database.init_db import initialize_database
from app.infrastructure.database.session import SessionLocal, engine
from app.infrastructure.monitoring import performance_monitor
from app.infrastructure.monitoring.middleware import (
    CacheMonitoringMiddleware,
    PerformanceMonitoringMiddleware,
)
from app.jobs.update_daily_metrics import update_metrics_for_market
from app.websocket.connection_manager import ConnectionManager
from app.websocket.data_stream_service import DataStreamService

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


class DatabaseInitializationError(Exception):
    """Raised when database initialization fails during application startup."""


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
            # Default seeding is disabled. Use a dedicated script if needed.
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
        traceback.print_exc()

    print("=== PROCEEDING WITH CACHE WARMING ===")

    # 新增：直接调用带 @cache 的 build_overview 进行正式预热，确保写入 Redis 缓存
    try:
        windows = ["5D", "20D", "60D"]
        providers = ["em", "ths"]
        for window in windows:
            for provider in providers:
                print(
                    f"[Prewarm] Industry overview window={window}, provider={provider} ..."
                )
                try:
                    data = await a_industries_fetcher.build_overview(window, provider)
                    size = len(data) if isinstance(data, list) else 0
                    print(
                        f"[Prewarm] Done window={window}, provider={provider}, size={size}"
                    )
                except Exception as inner_e:
                    print(
                        f"[Prewarm] Failed window={window}, provider={provider}: {inner_e}"
                    )
                # 轻微限速，避免对第三方源造成压力
                await asyncio.sleep(2)

        print(
            "A-share industry overview cache is warmed via build_overview for all windows/providers."
        )

        # 保存预热时间到Redis，并返回，避免执行旧的手动计算流程
        try:
            backend = FastAPICache.get_backend()
            current_time = datetime.now()
            await backend.set(
                INDUSTRY_WARMING_TIME_KEY, current_time.isoformat().encode("utf-8")
            )
            print(
                f"行业数据预热完成，下次预热时间: {current_time + timedelta(hours=12)}"
            )
        except Exception as set_e:
            print(f"保存预热时间失败: {set_e}")
    except Exception as e:
        print(f"预热 build_overview 发生异常: {e}")
    else:
        # 新增：预热完成后直接返回，避免下方旧逻辑再次拉取数据
        return

    # 旧的手动行业预热逻辑已删除，预热由 build_overview 统一负责。


def _is_test_environment() -> bool:
    """检测是否为测试环境，避免在单测中执行重型初始化。"""
    try:
        return (
            os.getenv("PYTEST_CURRENT_TEST") is not None
            or os.getenv("UNIT_TEST") == "1"
            or getattr(settings, "ENVIRONMENT", "").lower() == "test"
        )
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("正在启动应用...")

    # 测试环境下跳过重型初始化，保证单测快速稳定
    if _is_test_environment():
        logger.info("检测到测试环境，跳过数据库/缓存/调度器等重型初始化。")
        # 测试环境中仍需初始化最基本的 WebSocket 服务以支持集成测试
        try:
            app.state.connection_manager = ConnectionManager(
                heartbeat_interval_seconds=settings.WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS
            )
            app.state.data_stream_service = None
            logger.info("测试环境下WebSocket最小初始化完成")
        except Exception:
            logger.exception("测试环境下WebSocket最小初始化失败")
            app.state.connection_manager = None
            app.state.data_stream_service = None
        yield
        logger.info("测试环境下应用关闭。")
        return

    # 初始化数据库
    try:
        success = initialize_database()
    except Exception:
        logger.exception("启动时数据库初始化出错")
        raise

    if success:
        logger.info("✅ 数据库初始化成功")
    else:
        logger.error("❌ 数据库初始化失败")
        raise DatabaseInitializationError("数据库初始化失败")

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
    # 已在模块顶层导入 update_metrics_for_market 以满足 PLC0415

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
        if not hasattr(app.state, "background_tasks"):
            app.state.background_tasks = []
        warm_task = asyncio.create_task(warm_up_cache())
        app.state.background_tasks.append(warm_task)
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
        logger.info("正在初始化WebSocket服务...")

        connection_manager = ConnectionManager(
            heartbeat_interval_seconds=settings.WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS
        )
        redis_manager = RedisCacheManager()
        data_stream_service = DataStreamService(connection_manager, redis_manager)

        # Store services in app state for access in routes
        app.state.connection_manager = connection_manager
        app.state.data_stream_service = data_stream_service

        # Initialize WebSocket services in the router
        init_websocket_services(app, redis_manager)

        # Start data stream service
        await data_stream_service.start()
        logger.info("✅ WebSocket服务初始化并启动成功")

    except Exception:
        logger.exception("❌ WebSocket服务初始化失败")
        # 不抛出异常，允许应用继续启动( WebSocket功能可能不可用 )
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
    except Exception:
        logger.exception("停止WebSocket服务时出错")

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


# 路由注册函数：测试环境下仅注册 analytics 路由，正常环境注册全部路由
def _register_routers(app: FastAPI) -> None:
    if _is_test_environment():
        # 仅注册单测所需的 Analytics 路由，减少无关模块导入和副作用
        app.include_router(
            analytics_endpoints.router, prefix="/api/analytics", tags=["Analytics"]
        )
        return

    # 非测试环境：延迟导入并注册全部路由
    # Imports moved to top-level to comply with PLC0415
    app.include_router(auth_v1.router, prefix="/api/v1", tags=["auth"])
    app.include_router(users_v1.router, prefix="/api/v1", tags=["users"])
    app.include_router(
        watchlist_v1.router, prefix="/api/v1/watchlist", tags=["watchlist"]
    )
    app.include_router(stocks_v1.router, prefix="/api/v1/stocks", tags=["stocks"])
    app.include_router(
        cached_stocks_v1.router,
        prefix="/api/v1/cached-stocks",
        tags=["cached-stocks"],
    )
    app.include_router(monitoring_v1.router, prefix="/api/v1", tags=["monitoring"])
    app.include_router(cache_v1.router, prefix="/api/v1", tags=["cache"])
    app.include_router(admin_v1.router, prefix="/api/v1/admin", tags=["admin"])
    app.include_router(backtest_v1.router, prefix="/api/v1/backtest", tags=["backtest"])
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
    app.include_router(
        asset_config_v1.router, prefix="/api/v1/asset-config", tags=["asset-config"]
    )
    app.include_router(health_v1.router, prefix="/api/v1/health", tags=["health"])
    app.include_router(websocket_v1.router, prefix="/api/v1/ws", tags=["websocket"])

    # 同时注册 analytics 路由
    app.include_router(
        analytics_endpoints.router, prefix="/api/analytics", tags=["Analytics"]
    )


# 注册路由
_register_routers(app)


@app.get("/")
def read_root():
    return {"message": "Welcome to ChronoRetrace API"}


@app.get("/health")
def health_check():
    """简单的健康检查端点"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
