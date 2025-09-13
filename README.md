# ChronoRetrace

[![CI/CD Pipeline](https://github.com/codeway3/ChronoRetrace/actions/workflows/ci.yml/badge.svg)](https://github.com/codeway3/ChronoRetrace/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**English** | **[中文](./README_CN.md)**

**ChronoRetrace** is a full-stack financial data analysis and backtesting platform designed for quantitative analysts, investors, and developers. It provides a powerful web interface to fetch, visualize, and analyze historical stock market data, with a primary focus on A-shares and US stocks.


---

## ✨ Key Features

### 📊 Data & Analytics
-   **Multi-Market Data**: Fetches and displays data for A-shares, US stocks, and major cryptocurrencies.
-   **Futures and Options**: Fetches and displays data for futures and options.
-   **Interactive Charts**: Utilizes ECharts to provide responsive, interactive K-line (candlestick) charts with time range selection and key Moving Averages (MA5, MA10, MA20, MA60).
-   **Financial Data Overview**: Displays key performance indicators (KPIs), annual earnings, and corporate actions for selected stocks.
-   **Strategy Backtesting**: A flexible backtesting engine to test investment strategies with comprehensive performance metrics.
-   **Stock Screener**: Advanced filtering system to discover stocks based on technical and fundamental criteria.

### 🔐 Security & Authentication
-   **User Authentication**: Complete JWT-based authentication system with registration, login, and profile management.
-   **Role-Based Access**: Multi-level user permissions and access control.
-   **Session Management**: Secure session handling with token refresh capabilities.

### ⚡ Performance & Infrastructure
-   **Redis Caching**: Multi-layer caching system for optimal performance and reduced API calls.
-   **Performance Monitoring**: Real-time system metrics, response time tracking, and resource usage monitoring.
-   **Data Quality Assurance**: Automated data validation, deduplication, and integrity checks.
-   **API Rate Limiting**: Intelligent request throttling to ensure system stability.
-   **Database Optimization**: Automated indexing and query optimization for faster data retrieval.

### 🛠️ Developer Experience
-   **Modern Tech Stack**: Built with FastAPI on the backend for high performance and React on the frontend for a responsive user experience.
-   **Comprehensive Testing**: Unit and integration tests with high code coverage.
-   **CI/CD Pipeline**: Automated testing, linting, and security checks.
-   **Code Quality**: Enforced code standards with Ruff, Bandit, and Safety checks.

## 🚀 Quick Start

### One-Click Deployment (Recommended)

```bash
# Clone the repository
git clone https://github.com/codeway3/ChronoRetrace.git
cd ChronoRetrace

# Run the deployment script
./quick-deploy.sh
```

**That's it!** The script will:
- ✅ Detect your system environment
- ✅ Install all dependencies automatically
- ✅ Configure database and cache
- ✅ Start both frontend and backend services

**Access the application:**
- 🌐 Frontend: http://localhost:3000
- 🔧 Backend API: http://localhost:8000
- 👤 Admin Panel: http://localhost:8000/admin

**Default credentials:** `admin` / `admin123`

### Supported Systems
- ✅ macOS 10.15+
- ✅ Ubuntu 18.04+
- ✅ Automatic Docker detection

### Need Help?
- 📖 [Quick Deploy Guide](DEPLOY.md)
- 📚 [Detailed Documentation](docs/deployment.md)
- 🐛 [Troubleshooting](docs/deployment.md#故障排除)

---

## 🛠️ Technology Stack

| Area      | Technology                                                                                             |
| :-------- | :----------------------------------------------------------------------------------------------------- |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy, Uvicorn, Pandas, Pydantic, JWT Authentication                       |
| **Frontend**| React.js, Node.js 20+, ECharts for React, Ant Design, Axios, Context API                               |
| **Database**| SQLite (for development), PostgreSQL (recommended for production)                                      |
| **Caching** | Redis for multi-layer caching, session storage, and rate limiting                                      |
| **Monitoring** | Custom performance metrics, system resource tracking, response time analysis                         |
| **Security** | JWT tokens, bcrypt password hashing, input validation, API rate limiting                              |
| **DevOps**  | GitHub Actions for CI/CD, Ruff for linting, Pytest for testing, Bandit & Safety for security          |
| **Data Sources** | Akshare, yfinance, Baostock, CryptoCompare, and other financial data APIs                          |


## 🚀 Getting Started

Follow these instructions to set up and run the project on your local machine.

### 📋 Prerequisites

### System Requirements
-   **Operating System**: Ubuntu 18.04+, macOS 10.15+, or Windows 10+ (with WSL)
-   **Memory**: Minimum 4GB RAM (8GB recommended for production)
-   **Storage**: At least 2GB free disk space
-   **Network**: Internet connection for data fetching and package installation

### Software Dependencies
-   **Python**: Version 3.11 or newer
-   **Node.js**: Version 18 or newer (for the frontend)
-   **Redis**: Version 6.0 or newer (for caching and session management)
-   **(Optional) PostgreSQL**: Version 12+ for production deployment
-   **(Optional) Tushare API Token**: Some data fetchers may require an API token from [Tushare](https://tushare.pro/). If needed, register and place your token in the backend's `.env` file

#### Installing Redis

**macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**Windows:**
Download and install Redis from the [official releases](https://github.com/microsoftarchive/redis/releases) or use WSL.

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
cp .env.example .env

# Edit .env file and configure the following:
# - Database settings (SQLite for dev, PostgreSQL for production)
# - Redis connection (default: redis://localhost:6379)
# - JWT secret key for authentication
# - API tokens (Tushare, etc.) if needed
# - Performance monitoring settings

# Create a virtual environment and activate it
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt

# Initialize the database (creates tables and indexes)
python -c "from app.infrastructure.database.init_db import init_database; init_database()"

# Run the development server (recommended)
python start_dev.py

# Alternative methods:
# ./run_server.sh
# or: uvicorn app.main:app --reload --reload-dir .
```

**Available endpoints:**
- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- Metrics: `http://127.0.0.1:8000/metrics`

### 3. Frontend Setup

The frontend React app runs on port 3000 (or 3001 if 3000 is occupied).

```bash
# Navigate to the frontend directory from the project root
cd frontend

# Install dependencies
npm install

# Run the development server
npm start

# For custom port (if needed)
PORT=3001 npm start
```

**Available pages:**
- Home Dashboard: `http://localhost:3000/`
- Stock Analysis: `http://localhost:3000/analysis`
- Backtesting: `http://localhost:3000/backtest`
- Stock Screener: `http://localhost:3000/screener`
- User Authentication: `http://localhost:3000/login` & `http://localhost:3000/register`
- User Profile: `http://localhost:3000/profile`

The application should automatically open in your browser at `http://localhost:3000`.

## 📂 Project Structure

```
ChronoRetrace/
├── .github/                    # GitHub Actions Workflows
│   └── workflows/
│       └── ci-cd.yml           # CI/CD pipeline configuration
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── analytics/          # Analytics service modules
│   │   │   ├── backtesting/    # Backtesting functionality
│   │   │   └── screener/       # Stock screener
│   │   ├── api/                # API routing layer
│   │   │   └── v1/             # API v1 version
│   │   │       ├── auth/       # Authentication endpoints
│   │   │       ├── users/      # User management
│   │   │       ├── stocks/     # Stock data endpoints
│   │   │       └── analytics/  # Analytics endpoints
│   │   ├── core/               # Core configuration
│   │   │   ├── auth/           # JWT authentication
│   │   │   ├── config.py       # Application settings
│   │   │   └── security.py     # Security utilities
│   │   ├── data/               # Data layer
│   │   │   ├── fetchers/       # Data fetchers
│   │   │   ├── managers/       # Data managers
│   │   │   └── quality/        # Data quality control
│   │   ├── infrastructure/     # Infrastructure layer
│   │   │   ├── database/       # Database models and sessions
│   │   │   ├── cache/          # Redis caching
│   │   │   ├── monitoring/     # Performance monitoring
│   │   │   └── performance/    # Performance optimization
│   │   ├── jobs/               # Scheduled tasks
│   │   ├── schemas/            # Pydantic data models
│   │   └── services/           # Business logic services
│   ├── config/                 # Configuration files
│   │   └── performance.yaml    # Performance settings
│   ├── docs/                   # Documentation
│   │   ├── cache_architecture_design.md
│   │   ├── deployment.md
│   │   └── user_auth_development_plan.md
│   ├── tests/                  # Test files
│   │   ├── integration/        # Integration tests
│   │   ├── unit/               # Unit tests
│   │   └── conftest.py         # Test configuration
│   ├── .env.example            # Environment variables example
│   ├── requirements.txt        # Python dependencies
│   ├── requirements-dev.txt    # Development dependencies
│   └── pyproject.toml          # Project configuration
├── frontend/                   # React Frontend
│   ├── public/
│   └── src/
│       ├── api/                # API calls
│       ├── components/         # React components
│       ├── contexts/           # React contexts (Auth, etc.)
│       ├── layouts/            # Page layouts
│       └── pages/              # Page components
│           ├── auth/           # Authentication pages
│           ├── analysis/       # Stock analysis
│           ├── backtest/       # Backtesting interface
│           └── screener/       # Stock screener
├── enhance_plan.md             # Original enhancement plan
├── enhance_plan_v2.md          # Updated optimization roadmap
├── .gitignore
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── README.md
```

## 🎯 Usage Guide

### Authentication
1. **Register**: Create a new account at `/register`
2. **Login**: Sign in at `/login` to access personalized features
3. **Profile**: Manage your account settings at `/profile`

### Stock Analysis
1. **Search Stocks**: Use the search functionality to find stocks by symbol or name
2. **View Charts**: Interactive candlestick charts with technical indicators
3. **Financial Data**: Access key metrics, earnings, and corporate actions

### Backtesting
1. **Strategy Setup**: Configure your investment strategy parameters
2. **Historical Testing**: Run backtests on historical data
3. **Performance Analysis**: Review detailed performance metrics and charts

### Stock Screener
1. **Filter Criteria**: Set technical and fundamental filters
2. **Real-time Results**: Get updated stock recommendations
3. **Export Data**: Save filtered results for further analysis

### API Usage
- **REST API**: Full RESTful API available at `/docs`
- **Authentication**: JWT-based API authentication
- **Rate Limiting**: Automatic request throttling for fair usage
- **Caching**: Optimized response times with Redis caching

## 🚀 Deployment

### Quick Deploy
Use the provided script for one-click deployment:
```bash
./quick-deploy.sh
```

### Docker Deployment
```bash
# Development environment
docker-compose up -d

# Production environment
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment
For production Kubernetes deployment, see our [Kubernetes Guide](docs/deployment/kubernetes-deployment.md).

## 🔧 Development

### Code Quality
```bash
# Run linting
make lint

# Run tests
make test

# Format code
make format

# Security checks
make security
```

### Performance Monitoring
- **Metrics Endpoint**: `/metrics` for system performance data
- **Health Check**: `/health` for service status
- **Redis Monitoring**: Cache hit rates and performance stats

## 🔍 Troubleshooting

### Common Issues

**Backend won't start:**
- Check if Redis is running: `redis-cli ping`
- Verify Python version: `python --version` (should be 3.11+)
- Check database initialization: `python -c "from app.infrastructure.database.init_db import init_database; init_database()"`

**Frontend build errors:**
- Clear npm cache: `npm cache clean --force`
- Delete node_modules: `rm -rf node_modules && npm install`
- Check Node.js version: `node --version` (should be 18+)

**Database connection issues:**
- Verify database settings in `.env` file
- Check if PostgreSQL is running (for production)
- Ensure SQLite file permissions (for development)

**Performance issues:**
- Monitor Redis cache hit rates at `/metrics`
- Check system resources (CPU, memory)
- Review application logs in `logs/` directory

For more detailed troubleshooting, see our [Operations Guide](docs/deployment/operations-guide.md).

## ❓ FAQ

**Q: Can I use this for commercial purposes?**
A: Yes, this project is licensed under MIT License, which allows commercial use.

**Q: How do I add new data sources?**
A: Check the `backend/app/data/fetchers/` directory for examples and create your own data fetcher following the same pattern.

**Q: Is there a demo available?**
A: You can run the application locally using the quick-deploy script or Docker for a full demo experience.

**Q: How do I contribute new features?**
A: Please read our [Contributing Guidelines](CONTRIBUTING.md) and submit a pull request with your proposed changes.

## 📈 Changelog

### Version 2.0.0 (Latest)
- ✨ Enhanced performance monitoring and caching
- 🔒 Improved security with JWT authentication
- 📊 Advanced analytics and backtesting features
- 🐳 Docker and Kubernetes deployment support
- 🎨 Modern React UI with responsive design

### Version 1.0.0
- 🚀 Initial release with basic stock analysis features
- 📱 React frontend with basic charting
- 🔧 FastAPI backend with SQLite database
- 📊 Basic stock data fetching and display

For detailed changelog, see [CHANGELOG.md](CHANGELOG.md).

## 🤝 Contributing

Contributions are welcome! Whether it's bug reports, feature requests, or pull requests, we appreciate your help.

Please read our [**Contributing Guidelines**](CONTRIBUTING.md) to get started. Also, be sure to follow our [**Code of Conduct**](CODE_OF_CONDUCT.md).

## 📄 License

This project is licensed under the MIT License. See the [**LICENSE**](LICENSE) file for details.
