# ChronoRetrace 用户认证与数据安全体系开发计划

## 项目概述

本文档详细记录了ChronoRetrace项目用户认证与数据安全体系的设计方案和实施计划。该体系将为金融数据分析平台提供完整的用户管理、权限控制和数据安全保障。

## 开发目标

1. **用户认证体系**：实现完整的用户注册、登录、权限管理功能
2. **数据安全保障**：确保用户数据和金融数据的安全性
3. **管理员平台**：提供完善的后台管理功能
4. **扩展性设计**：为自选投资标的等未来功能预留空间

## 技术架构设计

### 1. 数据模型设计

#### 1.1 用户核心表 (User)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url VARCHAR(255),
    birth_date DATE,
    gender VARCHAR(10),
    profession VARCHAR(100),
    investment_experience VARCHAR(20), -- beginner, intermediate, advanced, expert
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    vip_level INTEGER DEFAULT 0, -- 0: normal, 1: vip, 2: premium
    email_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    password_reset_token VARCHAR(255),
    password_reset_expires DATETIME,
    email_verification_token VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME
);
```

#### 1.2 用户角色表 (UserRole)
```sql
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL, -- super_admin, admin, vip_user, normal_user, guest
    description TEXT,
    permissions TEXT, -- JSON格式存储权限列表
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_role_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES user_roles(id),
    FOREIGN KEY (assigned_by) REFERENCES users(id)
);
```

#### 1.3 用户偏好设置表 (UserPreferences)
```sql
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    theme_mode VARCHAR(20) DEFAULT 'light', -- light, dark, auto
    language VARCHAR(10) DEFAULT 'zh-CN',
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    currency VARCHAR(10) DEFAULT 'CNY',
    email_notifications BOOLEAN DEFAULT TRUE,
    sms_notifications BOOLEAN DEFAULT FALSE,
    push_notifications BOOLEAN DEFAULT TRUE,
    default_chart_type VARCHAR(20) DEFAULT 'candlestick',
    default_period VARCHAR(10) DEFAULT 'daily',
    preferred_indicators TEXT, -- JSON格式存储技术指标偏好
    risk_tolerance VARCHAR(20) DEFAULT 'moderate', -- conservative, moderate, aggressive
    investment_goal VARCHAR(50),
    investment_horizon VARCHAR(20), -- short_term, medium_term, long_term
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### 1.4 用户自选股票表 (UserWatchlist)
```sql
CREATE TABLE user_watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL, -- 自选分组名称
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE user_watchlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(20) NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    target_price DECIMAL(10,2),
    stop_loss_price DECIMAL(10,2),
    sort_order INTEGER DEFAULT 0,
    price_alert_enabled BOOLEAN DEFAULT FALSE,
    price_alert_threshold DECIMAL(5,2), -- 涨跌幅百分比
    volume_alert_enabled BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (watchlist_id) REFERENCES user_watchlists(id)
);
```

#### 1.5 用户投资组合表 (UserPortfolio)
```sql
CREATE TABLE user_portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    initial_capital DECIMAL(15,2),
    current_value DECIMAL(15,2),
    total_return DECIMAL(15,2),
    total_return_pct DECIMAL(5,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE user_portfolio_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    average_cost DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2),
    market_value DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2),
    unrealized_pnl_pct DECIMAL(5,2),
    first_purchase_date DATE,
    last_update_date DATE,
    FOREIGN KEY (portfolio_id) REFERENCES user_portfolios(id)
);

CREATE TABLE user_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    market VARCHAR(20) NOT NULL,
    transaction_type VARCHAR(10) NOT NULL, -- buy, sell
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    commission DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(15,2) NOT NULL,
    transaction_date DATETIME NOT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES user_portfolios(id)
);
```

#### 1.6 用户行为分析表 (UserBehavior)
```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_info TEXT,
    login_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    logout_at DATETIME,
    last_activity_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE user_activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    session_id INTEGER,
    action_type VARCHAR(50) NOT NULL, -- login, logout, view_page, search, filter, etc.
    resource_type VARCHAR(50), -- stock, portfolio, watchlist, etc.
    resource_id VARCHAR(100),
    details TEXT, -- JSON格式存储详细信息
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (session_id) REFERENCES user_sessions(id)
);
```

### 2. 认证与安全服务设计

#### 2.1 JWT认证服务
- **Token生成**：使用RS256算法，包含用户ID、角色、权限等信息
- **Token刷新**：实现refresh token机制，access token短期有效
- **Token验证**：中间件自动验证token有效性和权限

#### 2.2 密码安全
- **密码哈希**：使用bcrypt算法，salt rounds = 12
- **密码策略**：最少8位，包含大小写字母、数字和特殊字符
- **密码重置**：邮箱验证 + 临时token机制

#### 2.3 双因子认证
- **TOTP支持**：集成Google Authenticator等应用
- **备用码**：提供一次性备用验证码
- **短信验证**：可选的短信验证码功能

### 3. API接口设计

#### 3.1 认证相关接口
```
POST /api/v1/auth/register - 用户注册
POST /api/v1/auth/login - 用户登录
POST /api/v1/auth/logout - 用户登出
POST /api/v1/auth/refresh - 刷新token
POST /api/v1/auth/forgot-password - 忘记密码
POST /api/v1/auth/reset-password - 重置密码
POST /api/v1/auth/verify-email - 邮箱验证
POST /api/v1/auth/enable-2fa - 启用双因子认证
POST /api/v1/auth/verify-2fa - 验证双因子认证
```

#### 3.2 用户管理接口
```
GET /api/v1/users/profile - 获取用户资料
PUT /api/v1/users/profile - 更新用户资料
GET /api/v1/users/preferences - 获取用户偏好
PUT /api/v1/users/preferences - 更新用户偏好
POST /api/v1/users/change-password - 修改密码
DELETE /api/v1/users/account - 删除账户
```

#### 3.3 自选股接口
```
GET /api/v1/watchlists - 获取自选股列表
POST /api/v1/watchlists - 创建自选股分组
PUT /api/v1/watchlists/{id} - 更新自选股分组
DELETE /api/v1/watchlists/{id} - 删除自选股分组
POST /api/v1/watchlists/{id}/items - 添加股票到自选
DELETE /api/v1/watchlists/{id}/items/{symbol} - 从自选移除股票
```

#### 3.4 管理员接口
```
GET /api/v1/admin/users - 用户列表管理
PUT /api/v1/admin/users/{id}/status - 用户状态管理
GET /api/v1/admin/system/stats - 系统统计信息
GET /api/v1/admin/system/logs - 系统日志查看
POST /api/v1/admin/announcements - 发布系统公告
```

### 4. 安全防护机制

#### 4.1 API限流
- **用户级限流**：每用户每分钟最多100次请求
- **IP级限流**：每IP每分钟最多500次请求
- **接口级限流**：敏感接口（如登录）更严格的限制

#### 4.2 安全中间件
- **CORS配置**：严格的跨域资源共享策略
- **CSRF防护**：防止跨站请求伪造攻击
- **XSS防护**：输入验证和输出编码
- **SQL注入防护**：参数化查询和输入验证

#### 4.3 数据加密
- **传输加密**：强制HTTPS，TLS 1.3
- **存储加密**：敏感数据AES-256加密
- **密钥管理**：环境变量存储，定期轮换

## 实施计划

### 第一阶段：核心认证功能 (Week 1-2)

1. **数据模型实现**
   - 创建用户相关数据模型
   - 实现数据库迁移脚本
   - 添加索引优化

2. **认证服务开发**
   - JWT认证服务
   - 密码加密工具
   - 邮箱验证服务

3. **基础API接口**
   - 用户注册/登录/登出
   - 用户资料管理
   - 密码重置功能

### 第二阶段：权限管理和安全加固 (Week 3-4)

1. **权限管理系统**
   - 角色权限模型
   - 权限验证中间件
   - 管理员后台基础功能

2. **安全防护**
   - API限流中间件
   - 安全头设置
   - 输入验证和过滤

3. **双因子认证**
   - TOTP集成
   - 备用码生成
   - 验证流程

### 第三阶段：高级功能和优化 (Week 5-6)

1. **自选股功能**
   - 自选股数据模型
   - 自选股管理API
   - 价格提醒功能

2. **用户行为分析**
   - 行为日志记录
   - 统计分析功能
   - 异常行为检测

3. **管理员平台完善**
   - 用户管理界面
   - 系统监控面板
   - 数据统计报表

### 第四阶段：测试和部署 (Week 7-8)

1. **全面测试**
   - 单元测试覆盖
   - 集成测试
   - 安全测试
   - 性能测试

2. **文档完善**
   - API文档
   - 部署文档
   - 用户手册

3. **生产部署**
   - 环境配置
   - 数据迁移
   - 监控告警

## 默认管理员账号

```python
# 系统初始化时创建的默认管理员账号
DEFAULT_ADMIN = {
    "username": "admin",
    "email": "admin@chronoretrace.com",
    "password": "ChronoAdmin2024!",  # 首次登录强制修改
    "full_name": "系统管理员",
    "role": "super_admin",
    "is_active": True,
    "email_verified": True
}
```

## 配置要求

### 环境变量
```bash
# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 邮箱配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# 安全配置
SECRET_KEY=your-super-secret-key
PASSWORD_SALT_ROUNDS=12
API_RATE_LIMIT_PER_MINUTE=100

# 双因子认证
TOTP_ISSUER=ChronoRetrace
TOTP_ALGORITHM=SHA1
```

### 依赖包
```txt
# 认证相关
pyjwt[crypto]==2.8.0
passlib[bcrypt]==1.7.4
pyotp==2.9.0

# 邮箱服务
fastapi-mail==1.4.1

# 限流
slowapi==0.1.9

# 验证
pydantic[email]==2.5.0
```

## 安全检查清单

- [ ] 密码强度验证
- [ ] JWT token安全配置
- [ ] API限流实施
- [ ] 输入验证和过滤
- [ ] SQL注入防护
- [ ] XSS防护
- [ ] CSRF防护
- [ ] HTTPS强制使用
- [ ] 敏感数据加密
- [ ] 日志记录和监控
- [ ] 错误信息安全处理
- [ ] 会话管理安全

## 性能优化建议

1. **数据库优化**
   - 合适的索引策略
   - 查询优化
   - 连接池配置

2. **缓存策略**
   - Redis缓存用户会话
   - 权限信息缓存
   - 频繁查询结果缓存

3. **异步处理**
   - 邮件发送异步化
   - 日志记录异步化
   - 数据统计后台处理

## 监控和告警

1. **安全监控**
   - 异常登录检测
   - 暴力破解监控
   - 权限异常使用

2. **性能监控**
   - API响应时间
   - 数据库查询性能
   - 系统资源使用

3. **业务监控**
   - 用户注册趋势
   - 活跃用户统计
   - 功能使用分析

## 后续扩展规划

1. **投资组合管理**
   - 完整的持仓管理
   - 收益分析
   - 风险评估

2. **社交功能**
   - 投资想法分享
   - 跟投功能
   - 专家观点

3. **智能推荐**
   - 个性化推荐
   - 机器学习算法
   - 用户画像分析

4. **移动端支持**
   - 移动端API优化
   - 推送通知
   - 离线功能

---

*本文档将随着开发进展持续更新，确保实施过程中的准确性和完整性。*
