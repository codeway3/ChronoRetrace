from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load .env file from the backend directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    TUSHARE_API_TOKEN: str = os.getenv("TUSHARE_API_TOKEN", "")
    ALPHAVANTAGE_API_KEY: str = os.getenv("ALPHAVANTAGE_API_KEY", "")
    DATABASE_URL: str = "sqlite:///./chrono_retrace.db"
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0") # Add Redis URL

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
