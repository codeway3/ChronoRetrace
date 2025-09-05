# ChronoRetrace

[![CI/CD Pipeline](https://github.com/codeway3/ChronoRetrace/actions/workflows/ci.yml/badge.svg)](https://github.com/codeway3/ChronoRetrace/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ChronoRetrace** is a full-stack financial data analysis and backtesting platform designed for quantitative analysts, investors, and developers. It provides a powerful web interface to fetch, visualize, and analyze historical stock market data, with a primary focus on A-shares and US stocks.


---

## ✨ Key Features

-   **Multi-Market Data**: Fetches and displays data for A-shares, US stocks, and major cryptocurrencies.
-   **Futures and Options**: Fetches and displays data for futures and options.
-   **Interactive Charts**: Utilizes ECharts to provide responsive, interactive K-line (candlestick) charts with time range selection and key Moving Averages (MA5, MA10, MA20, MA60).
-   **Financial Data Overview**: Displays key performance indicators (KPIs), annual earnings, and corporate actions for selected stocks.
-   **Strategy Backtesting**: A flexible backtesting engine to test investment strategies. Comes with a simple "buy and hold" strategy as a baseline.
-   **Modern Tech Stack**: Built with FastAPI on the backend for high performance and React on the frontend for a responsive user experience.
-   **Persistent Storage**: Uses a database to cache financial data, reducing reliance on external API calls and improving performance.

## 🛠️ Technology Stack

| Area      | Technology                                                                                             |
| :-------- | :----------------------------------------------------------------------------------------------------- |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy, Uvicorn, Pandas, Pydantic                                           |
| **Frontend**| React.js, Node.js 20+, ECharts for React, Ant Design, Axios                                            |
| **Database**| SQLite (for development), PostgreSQL (recommended for production)                                      |
| **DevOps**  | GitHub Actions for CI/CD, Ruff for linting, Pytest for testing, ESLint for frontend linting             |
| **Data Sources** | Akshare, yfinance, Baostock, CryptoCompare, and other financial data APIs.                                      |


## 🚀 Getting Started

Follow these instructions to set up and run the project on your local machine.

### Prerequisites

-   **Python**: Version 3.10 or newer.
-   **Node.js**: Version 20.0 or newer.
-   **(Optional) Tushare API Token**: Some data fetchers may require an API token from [Tushare](https://tushare.pro/). If needed, register and place your token in the backend's `.env` file.

### 1. Clone the Repository

```bash
git clone https://github.com/codeway3/ChronoRetrace.git
cd ChronoRetrace
```

### 2. Backend Setup

The backend server runs on port 8000.

```bash
# Navigate to the backend directory
cd backend

# Create and configure your environment file
# (Add your API tokens here if needed)
cp .env.example .env

# Create a virtual environment and activate it
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt

# Run the development server (recommended)
python start_dev.py

# Alternative methods:
# ./run_server.sh
# or: uvicorn app.main:app --reload --reload-dir .
```
The API documentation will be available at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup

The frontend React app runs on port 3000.

```bash
# Navigate to the frontend directory from the project root
cd frontend

# Install dependencies
npm install

# Run the development server
npm start
```
The application should automatically open in your browser at `http://localhost:3000`.

## 📂 Project Structure

```
ChronoRetrace/
├── .github/                    # GitHub Actions Workflows
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── analytics/          # Analytics service modules
│   │   │   ├── backtesting/    # Backtesting functionality
│   │   │   └── screener/       # Stock screener
│   │   ├── api/                # API routing layer
│   │   │   └── v1/             # API v1 version
│   │   ├── core/               # Core configuration
│   │   ├── data/               # Data layer
│   │   │   ├── fetchers/       # Data fetchers
│   │   │   │   ├── stock_fetchers/   # Stock data fetchers
│   │   │   │   └── market_fetchers/  # Market data fetchers
│   │   │   ├── managers/       # Data managers
│   │   │   └── quality/        # Data quality control
│   │   ├── db/                 # Database models and sessions
│   │   ├── infrastructure/     # Infrastructure layer
│   │   │   ├── database/       # Database related
│   │   │   └── performance/    # Performance optimization
│   │   ├── jobs/               # Scheduled tasks
│   │   ├── schemas/            # Pydantic data models
│   │   └── services/           # Business logic services
│   ├── tests/                  # Test files
│   │   ├── integration/        # Integration tests
│   │   └── unit/               # Unit tests
│   ├── .env.example            # Environment variables example
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React 前端
│   ├── public/
│   └── src/
│       ├── api/                # API calls
│       ├── components/         # React components
│       ├── layouts/            # Page layouts
│       └── pages/              # Page components
├── .gitignore
├── LICENSE
├── CONTRIBUTING.md
├── REFACTOR_REPORT.md          # Refactoring report
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Whether it's bug reports, feature requests, or pull requests, we appreciate your help.

Please read our [**Contributing Guidelines**](CONTRIBUTING.md) to get started. Also, be sure to follow our [**Code of Conduct**](CODE_OF_CONDUCT.md).

## 📄 License

This project is licensed under the MIT License. See the [**LICENSE**](LICENSE) file for details.
