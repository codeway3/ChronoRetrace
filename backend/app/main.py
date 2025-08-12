from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
import logging
import warnings
from app.api.v1 import stocks as stocks_v1
from app.api.v1 import admin as admin_v1
from app.api.v1 import backtest as backtest_v1
from app.api.v1 import crypto as crypto_v1
from app.api.v1 import commodities as commodities_v1
from app.db.session import engine, SessionLocal
from app.db import models
from app.core.config import settings

# Suppress the specific FutureWarning from baostock
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="The frame.append method is deprecated and will be removed from pandas in a future version. Use pandas.concat instead.",
    module="baostock.data.resultset",
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("yfinance").setLevel(
    logging.WARNING
)  # Quieten yfinance's debug messages
logging.getLogger("urllib3").setLevel(logging.INFO)  # Quieten urllib3's debug messages


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    print("Application startup...")
    create_db_and_tables()

    # Initialize FastAPI-Cache with Redis backend
    redis = aioredis.from_url(
        settings.REDIS_URL, encoding="utf8", decode_responses=True
    )
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    print("FastAPI-Cache initialized with Redis.")

    print("Application startup complete.")
    yield
    # On shutdown
    print("Application shutdown.")


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




@app.get("/")
def read_root():
    return {"message": "Welcome to ChronoRetrace API"}
