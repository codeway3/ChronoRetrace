from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache # New import
from fastapi_cache.backends.redis import RedisBackend # New import
from redis import asyncio as aioredis # New import

import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from app.api.v1 import stocks as stocks_v1
from app.db.session import engine, SessionLocal
from app.db import models

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
            for stock in stocks_v1.DEFAULT_STOCKS:
                db_stock = models.StockInfo(ts_code=stock["ts_code"], name=stock["name"])
                db.add(db_stock)
            db.commit()
            print(f"{len(stocks_v1.DEFAULT_STOCKS)} default stocks seeded.")
        else:
            print("Stock info table already contains data. Skipping seeding.")
    finally:
        db.close()

from app.core.config import settings # New import

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    print("Application startup...")
    create_db_and_tables()

    # Initialize FastAPI-Cache with Redis backend
    redis = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=True)
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
    lifespan=lifespan
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

@app.get("/")
def read_root():
    return {"message": "Welcome to ChronoRetrace API"}
