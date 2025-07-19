# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ChronoRetrace** is a financial backtesting tool for analyzing historical market data across A-share and US stock markets. Built with FastAPI backend and React frontend, it fetches data from Tushare/AKShare (A-shares) and yfinance (US stocks), storing locally in SQLite for analysis.

## Architecture

### Backend (FastAPI)
- **Entry**: `backend/app/main.py:app` - FastAPI app with CORS, Redis caching, and auto DB seeding
- **API**: `backend/app/api/v1/stocks.py` - REST endpoints for stocks, fundamentals, corporate actions, earnings
- **Services**: Modular fetchers in `backend/app/services/`:
  - `data_fetcher.py` - Main orchestrator routing A-share vs US stock requests
  - `a_share_fetcher.py` - AKShare/Baostock integration for Chinese markets
  - `us_stock_fetcher.py` - yfinance integration for US markets
  - `db_writer.py` - SQLAlchemy ORM persistence layer
- **Database**: SQLAlchemy models in `backend/app/db/models.py` with tables for stock data, info, fundamentals, actions, earnings
- **Config**: Environment-based settings in `backend/app/core/config.py`

### Frontend (React)
- **Entry**: `frontend/src/App.js` - React Router with market-specific dashboards
- **Routes**: `/a-share` and `/us-stock` endpoints for different markets
- **Components**: Ant Design + ECharts for stock visualization and financial data display
- **API**: `frontend/src/api/stockApi.js` - Axios client for backend communication

## Development Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload  # Start dev server at http://127.0.0.1:8000
```

### Frontend
```bash
npm install --prefix frontend
npm start --prefix frontend  # Start dev server at http://localhost:3000
```

### Environment Setup
1. Copy `backend/.env.example` to `backend/.env`
2. Add Tushare API token: `TUSHARE_API_TOKEN="YOUR_TOKEN_HERE"`
3. Optional: Configure `REDIS_URL` for caching (defaults to `redis://localhost:6379/0`)

## Key API Endpoints

- `GET /api/v1/stocks/list/all?market_type=A_share` - Get stock list
- `GET /api/v1/stocks/{stock_code}?interval=daily&market_type=A_share` - Get stock data
- `POST /api/v1/stocks/{symbol}/sync` - Trigger background data sync
- `GET /api/v1/stocks/{symbol}/fundamentals` - Get fundamental data
- `GET /api/v1/stocks/{symbol}/corporate-actions` - Get corporate actions
- `GET /api/v1/stocks/{symbol}/annual-earnings` - Get annual earnings

## Data Flow

1. **Initial Load**: App seeds default stocks on startup
2. **Stock Lists**: Cached locally, refreshed from AKShare/yfinance when stale
3. **Historical Data**: Fetched on-demand via AKShare/yfinance, not cached
4. **Financial Data**: Background sync fetches fundamentals/corporate actions/earnings into SQLite
5. **Market Types**: `A_share` (China) vs `US_stock` (US) determine data source and formatting

## Testing

Backend uses FastAPI's built-in testing utilities. Frontend uses React Testing Library via `npm test`.

## File Structure Highlights

- `backend/app/schemas/` - Pydantic models for API validation
- `backend/app/db/session.py` - SQLAlchemy session management
- `frontend/src/pages/` - Market-specific dashboard components
- `frontend/src/components/` - Reusable chart and data components