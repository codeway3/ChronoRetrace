# ChronoRetrace

[![CI/CD Pipeline](https://github.com/codeway3/ChronoRetrace/actions/workflows/ci.yml/badge.svg)](https://github.com/codeway3/ChronoRetrace/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](./README.md)** | **中文**

**ChronoRetrace** 是一个为量化分析师、投资者和开发者设计的全栈金融数据分析和回测平台。它提供了强大的Web界面来获取、可视化和分析历史股票市场数据，主要专注于A股和美股。

---

## ✨ 核心功能

### 📊 数据与分析
-   **多市场数据**：获取并显示A股、美股和主要加密货币的数据。
-   **期货和期权**：获取并显示期货和期权数据。
-   **交互式图表**：使用ECharts提供响应式、交互式K线（蜡烛图）图表，支持时间范围选择和关键移动平均线（MA5、MA10、MA20、MA60）。
-   **财务数据概览**：显示关键绩效指标（KPI）、年度收益和公司行为。
-   **策略回测**：灵活的回测引擎，用于测试投资策略并提供全面的性能指标。
-   **股票筛选器**：基于技术和基本面标准的高级过滤系统，用于发现股票。

### 🔐 安全与认证
-   **用户认证**：完整的基于JWT的认证系统，包括注册、登录和个人资料管理。
-   **基于角色的访问**：多级用户权限和访问控制。
-   **会话管理**：安全的会话处理和令牌刷新功能。

### ⚡ 性能与基础设施
-   **Redis缓存**：多层缓存系统，优化性能并减少API调用。
-   **性能监控**：实时系统指标、响应时间跟踪和资源使用监控。
-   **数据质量保障**：自动化数据验证、去重和完整性检查。
-   **API限流**：智能请求节流以确保系统稳定性。
-   **数据库优化**：自动索引和查询优化，实现更快的数据检索。

### 🛠️ 开发者体验
-   **现代技术栈**：后端使用FastAPI实现高性能，前端使用React提供响应式用户体验。
-   **全面测试**：单元测试和集成测试，具有高代码覆盖率。
-   **CI/CD流水线**：自动化测试、代码检查和安全检查。
-   **代码质量**：使用Ruff、Bandit和Safety检查强制执行代码标准。

## 🛠️ 技术栈

| 领域      | 技术                                                                                             |
| :-------- | :----------------------------------------------------------------------------------------------------- |
| **后端** | Python 3.10+, FastAPI, SQLAlchemy, Uvicorn, Pandas, Pydantic, JWT认证                       |
| **前端**| React.js, Node.js 20+, ECharts for React, Ant Design, Axios, Context API                               |
| **数据库**| SQLite（开发环境），PostgreSQL（生产环境推荐）                                      |
| **缓存** | Redis用于多层缓存、会话存储和限流                                      |
| **监控** | 自定义性能指标、系统资源跟踪、响应时间分析                         |
| **安全** | JWT令牌、bcrypt密码哈希、输入验证、API限流                              |
| **DevOps**  | GitHub Actions用于CI/CD、Ruff代码检查、Pytest测试、Bandit和Safety安全检查          |
| **数据源** | Akshare、yfinance、Baostock、CryptoCompare等金融数据API                          |


## 🚀 快速开始

按照以下说明在本地机器上设置和运行项目。

### 前置要求

-   **Python**：3.10或更新版本。
-   **Node.js**：20.0或更新版本。
-   **Redis**：6.0或更新版本（用于缓存和会话管理）。
-   **（可选）Tushare API令牌**：某些数据获取器可能需要来自[Tushare](https://tushare.pro/)的API令牌。如果需要，请注册并将令牌放在后端的`.env`文件中。

#### 安装Redis

**macOS（使用Homebrew）：**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian：**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**Windows：**
从[官方发布页面](https://github.com/microsoftarchive/redis/releases)下载并安装Redis，或使用WSL。

### 1. 克隆仓库

```bash
git clone https://github.com/codeway3/ChronoRetrace.git
cd ChronoRetrace
```

### 2. 后端设置

后端服务器运行在8000端口。

```bash
# 导航到后端目录
cd backend

# 创建并配置环境文件
cp .env.example .env

# 编辑.env文件并配置以下内容：
# - 数据库设置（开发环境用SQLite，生产环境用PostgreSQL）
# - Redis连接（默认：redis://localhost:6379）
# - JWT认证密钥
# - API令牌（Tushare等）如果需要
# - 性能监控设置

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows使用 `venv\Scripts\activate`

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（创建表和索引）
python -c "from app.infrastructure.database.init_db import init_database; init_database()"

# 运行开发服务器（推荐）
python start_dev.py

# 其他方法：
# ./run_server.sh
# 或：uvicorn app.main:app --reload --reload-dir .
```

**可用端点：**
- API文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`
- 指标监控：`http://127.0.0.1:8000/metrics`

### 3. 前端设置

前端React应用运行在3000端口（如果3000被占用则使用3001）。

```bash
# 从项目根目录导航到前端目录
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm start

# 自定义端口（如果需要）
PORT=3001 npm start
```

**可用页面：**
- 主页仪表板：`http://localhost:3000/`
- 股票分析：`http://localhost:3000/analysis`
- 回测：`http://localhost:3000/backtest`
- 股票筛选器：`http://localhost:3000/screener`
- 用户认证：`http://localhost:3000/login` 和 `http://localhost:3000/register`
- 用户资料：`http://localhost:3000/profile`

应用程序应该会在浏览器中自动打开`http://localhost:3000`。

## 📂 项目结构

```
ChronoRetrace/
├── .github/                    # GitHub Actions工作流
│   └── workflows/
│       └── ci.yml              # CI/CD流水线配置
├── backend/                    # FastAPI后端
│   ├── app/
│   │   ├── analytics/          # 分析服务模块
│   │   │   ├── backtesting/    # 回测功能
│   │   │   └── screener/       # 股票筛选器
│   │   ├── api/                # API路由层
│   │   │   └── v1/             # API v1版本
│   │   │       ├── auth/       # 认证端点
│   │   │       ├── users/      # 用户管理
│   │   │       ├── stocks/     # 股票数据端点
│   │   │       └── analytics/  # 分析端点
│   │   ├── core/               # 核心配置
│   │   │   ├── auth/           # JWT认证
│   │   │   ├── config.py       # 应用设置
│   │   │   └── security.py     # 安全工具
│   │   ├── data/               # 数据层
│   │   │   ├── fetchers/       # 数据获取器
│   │   │   ├── managers/       # 数据管理器
│   │   │   └── quality/        # 数据质量控制
│   │   ├── infrastructure/     # 基础设施层
│   │   │   ├── database/       # 数据库模型和会话
│   │   │   ├── cache/          # Redis缓存
│   │   │   ├── monitoring/     # 性能监控
│   │   │   └── performance/    # 性能优化
│   │   ├── jobs/               # 定时任务
│   │   ├── schemas/            # Pydantic数据模型
│   │   └── services/           # 业务逻辑服务
│   ├── config/                 # 配置文件
│   │   └── performance.yaml    # 性能设置
│   ├── docs/                   # 文档
│   │   ├── cache_architecture_design.md
│   │   ├── deployment.md
│   │   └── user_auth_development_plan.md
│   ├── tests/                  # 测试文件
│   │   ├── integration/        # 集成测试
│   │   ├── unit/               # 单元测试
│   │   └── conftest.py         # 测试配置
│   ├── .env.example            # 环境变量示例
│   ├── requirements.txt        # Python依赖
│   ├── requirements-dev.txt    # 开发依赖
│   └── pyproject.toml          # 项目配置
├── frontend/                   # React前端
│   ├── public/
│   └── src/
│       ├── api/                # API调用
│       ├── components/         # React组件
│       ├── contexts/           # React上下文（认证等）
│       ├── layouts/            # 页面布局
│       └── pages/              # 页面组件
│           ├── auth/           # 认证页面
│           ├── analysis/       # 股票分析
│           ├── backtest/       # 回测界面
│           └── screener/       # 股票筛选器
├── enhance_plan.md             # 原始增强计划
├── enhance_plan_v2.md          # 更新的优化路线图
├── .gitignore
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
└── README.md
```

## 🎯 使用指南

### 认证
1. **注册**：在`/register`创建新账户
2. **登录**：在`/login`登录以访问个性化功能
3. **个人资料**：在`/profile`管理您的账户设置

### 股票分析
1. **搜索股票**：使用搜索功能按代码或名称查找股票
2. **查看图表**：带有技术指标的交互式蜡烛图
3. **财务数据**：访问关键指标、收益和公司行为

### 回测
1. **策略设置**：配置您的投资策略参数
2. **历史测试**：在历史数据上运行回测
3. **性能分析**：查看详细的性能指标和图表

### 股票筛选器
1. **过滤条件**：设置技术和基本面过滤器
2. **实时结果**：获取更新的股票推荐
3. **导出数据**：保存过滤结果以供进一步分析

### API使用
- **REST API**：完整的RESTful API可在`/docs`获得
- **认证**：基于JWT的API认证
- **限流**：自动请求节流以确保公平使用
- **缓存**：通过Redis缓存优化响应时间

## 🔧 开发

### 代码质量
```bash
# 运行代码检查
make lint

# 运行测试
make test

# 格式化代码
make format

# 安全检查
make security
```

### 性能监控
- **指标端点**：`/metrics`用于系统性能数据
- **健康检查**：`/health`用于服务状态
- **Redis监控**：缓存命中率和性能统计

## 🤝 贡献

欢迎贡献！无论是错误报告、功能请求还是拉取请求，我们都感谢您的帮助。

请阅读我们的[**贡献指南**](CONTRIBUTING.md)开始。同时，请务必遵循我们的[**行为准则**](CODE_OF_CONDUCT.md)。

## 📄 许可证

本项目采用MIT许可证。详情请参见[**LICENSE**](LICENSE)文件。