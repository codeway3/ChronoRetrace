# ChronoRetrace

[![CI/CD Pipeline](https://github.com/codeway3/ChronoRetrace/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/codeway3/ChronoRetrace/actions/workflows/ci-cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](./README.md)** | **中文**

**ChronoRetrace** 是一个为量化分析师、投资者和开发者设计的全栈金融数据分析和回测平台。它提供了强大的Web界面来获取、可视化和分析历史股票市场数据，主要专注于A股和美股。

---

## ✨ 核心功能

### 📊 数据与分析
-   **多市场数据**：获取并显示A股、美股和主要加密货币的数据。
-   **期货和期权**：获取并显示期货和期权数据。
-   **实时数据流**：基于WebSocket的实时数据推送服务，支持自动重连、心跳监控和多客户端连接。
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

## 🚀 快速开始

### 一键部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/codeway3/ChronoRetrace.git
cd ChronoRetrace

# 运行部署脚本
./quick-deploy.sh

# 部署并包含监控服务 (Prometheus, Grafana):
./quick-deploy.sh --with-monitoring
```

**就这么简单！** 脚本将会：
- ✅ 自动检测您的系统环境
- ✅ 自动安装所有依赖
- ✅ 配置数据库和缓存
- ✅ 启动前端和后端服务

**访问应用程序：**
- 🌐 前端：http://localhost:3000
- 🔧 后端API：http://localhost:8000
- 👤 管理面板：http://localhost:8000/admin

**默认凭据：** `admin` / `admin123`

**监控服务 (如果已部署):**
- 🔥 Prometheus: http://localhost:9090
- 📈 Grafana: http://localhost:3001 (默认: `admin` / `admin`)

### 支持的系统
- ✅ macOS 10.15+
- ✅ Ubuntu 18.04+
- ✅ 自动检测Docker环境

### 需要帮助？
- 📖 [快速部署指南](DEPLOY.md)
- 📚 [详细文档](docs/deployment.md)
- 🐛 [故障排除](docs/deployment.md#故障排除)

---

## 🛠️ 技术栈

| 领域      | 技术                                                                                             |
| :-------- | :----------------------------------------------------------------------------------------------------- |
| **后端** | Python 3.10+, FastAPI, SQLAlchemy, Uvicorn, Pandas, Pydantic, JWT认证                       |
| **前端**| React.js, Node.js 20+, ECharts for React, Ant Design, Axios, Context API                               |
| **实时通信** | WebSocket连接、自动重连、心跳监控、消息路由                                      |
| **数据库**| SQLite（开发环境），PostgreSQL（生产环境推荐）                                      |
| **缓存** | Redis用于多层缓存、会话存储和限流                                      |
| **监控** | 自定义性能指标、系统资源跟踪、响应时间分析                         |
| **安全** | JWT令牌、bcrypt密码哈希、输入验证、API限流                              |
| **DevOps**  | GitHub Actions用于CI/CD、Ruff代码检查、Pytest测试、Bandit和Safety安全检查          |
| **数据源** | Akshare、yfinance、Baostock、CryptoCompare等金融数据API                          |


## 📂 项目结构

```
ChronoRetrace/
├── .github/                    # GitHub Actions工作流
│   └── workflows/
│       └── ci-cd.yml           # CI/CD流水线配置
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
3. **实时更新**：订阅实时数据流，图表自动更新
4. **财务数据**：访问关键指标、收益和公司行为

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
- **WebSocket API**：实时数据流服务位于`/api/v1/ws/connect`
- **认证**：基于JWT的API认证
- **限流**：自动请求节流以确保公平使用
- **缓存**：通过Redis缓存优化响应时间

## 🚀 部署

### 快速部署
使用提供的脚本进行一键部署：
```bash
# 默认部署
./quick-deploy.sh

# 包含监控服务
./quick-deploy.sh --with-monitoring
```

### Docker部署
```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes部署
生产环境Kubernetes部署请参考我们的[Kubernetes指南](docs/deployment/kubernetes-deployment.md)。

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

## 🔍 故障排除

### 常见问题

**后端无法启动：**
- 检查Redis是否运行：`redis-cli ping`
- 验证Python版本：`python --version`（应为3.11+）
- 检查数据库初始化：`python -c "from app.infrastructure.database.init_db import init_database; init_database()"`

**前端构建错误：**
- 清除npm缓存：`npm cache clean --force`
- 删除node_modules：`rm -rf node_modules && npm install`
- 检查Node.js版本：`node --version`（应为18+）

**数据库连接问题：**
- 验证`.env`文件中的数据库设置
- 检查PostgreSQL是否运行（生产环境）
- 确保SQLite文件权限（开发环境）

**性能问题：**
- 在`/metrics`监控Redis缓存命中率
- 检查系统资源（CPU、内存）
- 查看`logs/`目录中的应用日志

更详细的故障排除请参考我们的[运维指南](docs/deployment/operations-guide.md)。

## ❓ 常见问题

**问：我可以将此项目用于商业用途吗？**
答：可以，本项目采用MIT许可证，允许商业使用。

**问：如何添加新的数据源？**
答：查看`backend/app/data/fetchers/`目录中的示例，按照相同模式创建您自己的数据获取器。

**问：有演示版本吗？**
答：您可以使用快速部署脚本或Docker在本地运行应用程序以获得完整的演示体验。

**问：如何贡献新功能？**
答：请阅读我们的[贡献指南](CONTRIBUTING.md)并提交包含您建议更改的拉取请求。

## 📈 更新日志

### 版本 2.0.0（最新）
- ✨ 增强的性能监控和缓存
- 🔒 通过JWT认证改进安全性
- 📊 高级分析和回测功能
- 🔄 WebSocket实时数据流，支持自动重连和心跳监控
- 🐳 Docker和Kubernetes部署支持
- 🎨 现代化响应式React UI设计

### 版本 1.0.0
- 🚀 具有基本股票分析功能的初始版本
- 📱 带有基本图表的React前端
- 🔧 使用SQLite数据库的FastAPI后端
- 📊 基本股票数据获取和显示

详细更新日志请参见[CHANGELOG.md](CHANGELOG.md)。

## 🤝 贡献

欢迎贡献！无论是错误报告、功能请求还是拉取请求，我们都感谢您的帮助。

请阅读我们的[**贡献指南**](CONTRIBUTING.md)开始。同时，请务必遵循我们的[**行为准则**](CODE_OF_CONDUCT.md)。

## 📄 许可证

本项目采用MIT许可证。详情请参见[**LICENSE**](LICENSE)文件。
