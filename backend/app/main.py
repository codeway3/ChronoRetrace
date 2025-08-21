import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
import logging
import warnings
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api.v1 import stocks as stocks_v1
from app.api.v1 import admin as admin_v1
from app.api.v1 import backtest as backtest_v1
from app.api.v1 import crypto as crypto_v1
from app.api.v1 import commodities as commodities_v1
from app.api.v1 import futures as futures_v1
from app.api.v1 import options as options_v1
from app.api.v1 import a_industries as a_industries_v1
from app.db.session import engine, SessionLocal
from app.db import models
from app.core.config import settings
from app.services import a_industries_fetcher

# Suppress the specific FutureWarning from baostock
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="The frame.append method is deprecated and will be removed from pandas in a future version. Use pandas.concat instead.",
    module="baostock.data.resultset",
)
# Suppress the warning from akshare about requests_html not being installed
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Certain functionality"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("yfinance").setLevel(
    logging.WARNING
)  # Quieten yfinance's debug messages
logging.getLogger("urllib3").setLevel(
    logging.INFO)  # Quieten urllib3's debug messages
logging.getLogger("apscheduler").setLevel(logging.WARNING)


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
    print("Warming up A-share industry overview cache for all windows (5D, 20D, 60D)...")
    try:
        windows = ["5D", "20D", "60D"]
        tasks = [a_industries_fetcher.build_overview(
            window) for window in windows]
        await asyncio.gather(*tasks)
        print("A-share industry overview cache is warmed up successfully for all windows.")
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
    scheduler.add_job(warm_up_cache, "interval",
                      hours=1, id="warm_up_cache_job")
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
app.include_router(futures_v1.router,
                   prefix="/api/v1/futures", tags=["futures"])
app.include_router(options_v1.router,
                   prefix="/api/v1/options", tags=["options"])
app.include_router(
    a_industries_v1.router, prefix="/api/v1/a-industries", tags=["a-industries"]
)


@app.get("/")
def read_root():
    return {"message": "Welcome to ChronoRetrace API"}
