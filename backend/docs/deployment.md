# ChronoRetrace 部署文档

本文档详细说明了 ChronoRetrace 系统的部署流程、配置要求和运维指南。

## 目录

- [系统要求](#系统要求)
- [环境准备](#环境准备)
- [部署流程](#部署流程)
- [配置说明](#配置说明)
- [性能优化](#性能优化)
- [监控和运维](#监控和运维)
- [故障排除](#故障排除)
- [升级指南](#升级指南)

## 系统要求

### 硬件要求

#### 最小配置
- CPU: 2核心
- 内存: 4GB RAM
- 存储: 50GB SSD
- 网络: 100Mbps

#### 推荐配置
- CPU: 4核心以上
- 内存: 8GB RAM 以上
- 存储: 200GB SSD 以上
- 网络: 1Gbps

#### 生产环境配置
- CPU: 8核心以上
- 内存: 16GB RAM 以上
- 存储: 500GB SSD 以上
- 网络: 1Gbps 以上

### 软件要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / macOS 11+
- **Python**: 3.9+
- **PostgreSQL**: 13+
- **Redis**: 6.0+
- **Docker**: 20.10+ (可选)
- **Docker Compose**: 1.29+ (可选)

## 环境准备

### 1. 系统更新

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y

# macOS
brew update && brew upgrade
```

### 2. 安装依赖

#### Python 环境

```bash
# 安装 Python 3.9+
sudo apt install python3.9 python3.9-pip python3.9-venv

# 或使用 pyenv
curl https://pyenv.run | bash
pyenv install 3.9.16
pyenv global 3.9.16
```

#### PostgreSQL 安装

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb

# macOS
brew install postgresql
brew services start postgresql
```

#### Redis 安装

```bash
# Ubuntu/Debian
sudo apt install redis-server

# CentOS/RHEL
sudo yum install redis

# macOS
brew install redis
brew services start redis
```

### 3. 数据库配置

#### PostgreSQL 配置

```bash
# 创建数据库用户
sudo -u postgres createuser --interactive chronoretrace

# 创建数据库
sudo -u postgres createdb chronoretrace_db -O chronoretrace

# 设置密码
sudo -u postgres psql -c "ALTER USER chronoretrace PASSWORD 'your_password';"
```

#### PostgreSQL 性能优化

编辑 `/etc/postgresql/13/main/postgresql.conf`:

```ini
# 内存配置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# 连接配置
max_connections = 100

# 检查点配置
checkpoint_completion_target = 0.9
wal_buffers = 16MB

# 日志配置
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000
```

#### Redis 配置

编辑 `/etc/redis/redis.conf`:

```ini
# 内存配置
maxmemory 512mb
maxmemory-policy allkeys-lru

# 持久化配置
save 900 1
save 300 10
save 60 10000

# 网络配置
bind 127.0.0.1
port 6379
timeout 300

# 安全配置
requirepass your_redis_password
```

## 部署流程

### 方式一：传统部署

#### 1. 克隆代码

```bash
git clone https://github.com/codeway3/ChronoRetrace.git
cd ChronoRetrace/backend
```

#### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 环境配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

#### 5. 数据库迁移

```bash
# 创建数据库表
python -m alembic upgrade head

# 初始化数据
python scripts/init_data.py
```

#### 6. 启动服务

```bash
# 开发环境
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产环境
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 方式二：Docker 部署

#### 1. 构建镜像

```bash
# 构建应用镜像
docker build -t chronoretrace:latest .
```

#### 2. 使用 Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://chronoretrace:password@db:5432/chronoretrace_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=chronoretrace_db
      - POSTGRES_USER=chronoretrace
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    command: redis-server --requirepass password
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

#### 3. 启动服务

```bash
docker-compose up -d
```

### 方式三：Kubernetes 部署

#### 1. 创建命名空间

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: chronoretrace
```

#### 2. 配置 ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chronoretrace-config
  namespace: chronoretrace
data:
  DATABASE_URL: "postgresql://chronoretrace:password@postgres:5432/chronoretrace_db"
  REDIS_URL: "redis://redis:6379/0"
```

#### 3. 部署应用

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chronoretrace-app
  namespace: chronoretrace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chronoretrace
  template:
    metadata:
      labels:
        app: chronoretrace
    spec:
      containers:
      - name: app
        image: chronoretrace:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: chronoretrace-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

## 配置说明

### 环境变量配置

创建 `.env` 文件:

```bash
# 数据库配置
DATABASE_URL=postgresql://chronoretrace:password@localhost:5432/chronoretrace_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis 配置
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_redis_password
REDIS_MAX_CONNECTIONS=50

# 应用配置
APP_NAME=ChronoRetrace
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=your_secret_key_here

# API 配置
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["*"]
MAX_REQUEST_SIZE=10485760

# 缓存配置
CACHE_DEFAULT_TTL=3600
CACHE_WARMING_ENABLED=true
CACHE_WARMING_BATCH_SIZE=100

# 监控配置
MONITORING_ENABLED=true
METRICS_COLLECTION_INTERVAL=60

# 日志配置
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/chronoretrace/app.log

# 外部服务配置
TUSHARE_TOKEN=your_tushare_token
TUSHARE_API_URL=http://api.tushare.pro
```

### 性能配置文件

使用 `config/performance.yaml` 进行详细配置，参考前面创建的配置文件。

## 性能优化

### 1. 应用层优化

#### 启用缓存预热

```python
# 在应用启动时执行
async def startup_event():
    await cache_warming_service.warm_cache()
```

#### 配置连接池

```python
# 数据库连接池
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=3600
)

# Redis 连接池
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50
)
```

### 2. 数据库优化

#### 创建索引

```sql
-- 股票数据查询索引
CREATE INDEX idx_daily_stock_metrics_ts_code_date 
ON daily_stock_metrics(ts_code, trade_date);

CREATE INDEX idx_daily_stock_metrics_date 
ON daily_stock_metrics(trade_date);

CREATE INDEX idx_daily_stock_metrics_volume_date 
ON daily_stock_metrics(volume, trade_date);

-- 股票信息索引
CREATE INDEX idx_stock_info_industry 
ON stock_info(industry);

CREATE INDEX idx_stock_info_list_date 
ON stock_info(list_date);
```

#### 分区表配置

```sql
-- 按日期分区
CREATE TABLE daily_stock_metrics_partitioned (
    LIKE daily_stock_metrics INCLUDING ALL
) PARTITION BY RANGE (trade_date);

-- 创建分区
CREATE TABLE daily_stock_metrics_2024_01 
PARTITION OF daily_stock_metrics_partitioned 
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 3. 缓存优化

#### 多级缓存策略

```python
# L1: 内存缓存（应用内）
# L2: Redis 缓存（分布式）
# L3: 数据库缓存（查询结果）

class MultiLevelCache:
    def __init__(self):
        self.l1_cache = {}
        self.l2_cache = redis_client
        
    async def get(self, key):
        # 先查 L1
        if key in self.l1_cache:
            return self.l1_cache[key]
            
        # 再查 L2
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value
            
        return None
```

### 4. 负载均衡配置

#### Nginx 配置

```nginx
upstream chronoretrace_backend {
    least_conn;
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8003 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.chronoretrace.com;
    
    location / {
        proxy_pass http://chronoretrace_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # 缓存配置
        proxy_cache api_cache;
        proxy_cache_valid 200 5m;
        proxy_cache_key $scheme$proxy_host$request_uri;
    }
}
```

## 监控和运维

### 1. 健康检查

#### 应用健康检查

```python
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database_health(),
        "redis": await check_redis_health(),
        "cache_warming": await check_cache_warming_health()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        },
        status_code=status_code
    )
```

#### 系统监控脚本

```bash
#!/bin/bash
# monitor.sh

# 检查应用状态
check_app() {
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ $response -eq 200 ]; then
        echo "App: OK"
    else
        echo "App: FAILED (HTTP $response)"
        # 发送告警
        send_alert "Application health check failed"
    fi
}

# 检查数据库连接
check_database() {
    pg_isready -h localhost -p 5432 -U chronoretrace
    if [ $? -eq 0 ]; then
        echo "Database: OK"
    else
        echo "Database: FAILED"
        send_alert "Database connection failed"
    fi
}

# 检查 Redis
check_redis() {
    redis-cli ping > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "Redis: OK"
    else
        echo "Redis: FAILED"
        send_alert "Redis connection failed"
    fi
}

# 发送告警
send_alert() {
    message=$1
    # 这里可以集成邮件、短信、Slack 等告警方式
    echo "ALERT: $message" | logger
}

# 执行检查
check_app
check_database
check_redis
```

### 2. 日志管理

#### 日志轮转配置

```bash
# /etc/logrotate.d/chronoretrace
/var/log/chronoretrace/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 chronoretrace chronoretrace
    postrotate
        systemctl reload chronoretrace
    endscript
}
```

#### 日志分析脚本

```bash
#!/bin/bash
# log_analysis.sh

LOG_FILE="/var/log/chronoretrace/app.log"
DATE=$(date +%Y-%m-%d)

# 分析错误日志
echo "=== Error Analysis for $DATE ==="
grep "ERROR" $LOG_FILE | grep $DATE | wc -l
echo "Total errors today"

# 分析慢查询
echo "\n=== Slow Queries ==="
grep "slow_query" $LOG_FILE | grep $DATE | head -10

# 分析API响应时间
echo "\n=== API Performance ==="
grep "response_time" $LOG_FILE | grep $DATE | \
    awk '{print $NF}' | sort -n | tail -10
```

### 3. 备份策略

#### 数据库备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/chronoretrace"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="chronoretrace_db"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 数据库备份
pg_dump -h localhost -U chronoretrace $DB_NAME | \
    gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Redis 备份
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis_backup_$DATE.rdb

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "*backup*" -mtime +30 -delete

echo "Backup completed: $DATE"
```

## 故障排除

### 常见问题

#### 1. 应用启动失败

**症状**: 应用无法启动，端口占用错误

**解决方案**:
```bash
# 检查端口占用
lsof -i :8000

# 杀死占用进程
kill -9 <PID>

# 或更换端口
uvicorn app.main:app --port 8001
```

#### 2. 数据库连接失败

**症状**: `connection refused` 或 `authentication failed`

**解决方案**:
```bash
# 检查数据库状态
sudo systemctl status postgresql

# 检查连接配置
psql -h localhost -U chronoretrace -d chronoretrace_db

# 检查防火墙
sudo ufw status
```

#### 3. Redis 连接问题

**症状**: 缓存功能异常，Redis 连接超时

**解决方案**:
```bash
# 检查 Redis 状态
redis-cli ping

# 检查配置
redis-cli config get "*"

# 重启 Redis
sudo systemctl restart redis
```

#### 4. 性能问题

**症状**: 响应时间慢，CPU/内存使用率高

**诊断步骤**:
```bash
# 检查系统资源
top
htop
iostat

# 检查数据库性能
psql -c "SELECT * FROM pg_stat_activity;"

# 检查慢查询
grep "slow_query" /var/log/chronoretrace/app.log

# 检查缓存命中率
redis-cli info stats
```

### 故障恢复流程

#### 1. 应用故障恢复

```bash
#!/bin/bash
# recovery.sh

echo "Starting recovery process..."

# 停止应用
sudo systemctl stop chronoretrace

# 检查并修复数据库
psql -U chronoretrace -d chronoretrace_db -c "VACUUM ANALYZE;"

# 清理缓存
redis-cli FLUSHALL

# 重启服务
sudo systemctl start postgresql
sudo systemctl start redis
sudo systemctl start chronoretrace

# 验证服务状态
curl http://localhost:8000/health

echo "Recovery completed"
```

#### 2. 数据恢复

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 停止应用
sudo systemctl stop chronoretrace

# 恢复数据库
gunzip -c $BACKUP_FILE | psql -U chronoretrace -d chronoretrace_db

# 重启应用
sudo systemctl start chronoretrace

echo "Data restored from $BACKUP_FILE"
```

## 升级指南

### 1. 应用升级

#### 滚动升级流程

```bash
#!/bin/bash
# rolling_upgrade.sh

NEW_VERSION=$1
SERVERS=("server1" "server2" "server3" "server4")

for server in "${SERVERS[@]}"; do
    echo "Upgrading $server..."
    
    # 从负载均衡器移除
    nginx_remove_server $server
    
    # 等待现有连接完成
    sleep 30
    
    # 停止应用
    ssh $server "sudo systemctl stop chronoretrace"
    
    # 部署新版本
    ssh $server "cd /opt/chronoretrace && git pull && git checkout $NEW_VERSION"
    ssh $server "cd /opt/chronoretrace && pip install -r requirements.txt"
    
    # 运行迁移
    ssh $server "cd /opt/chronoretrace && alembic upgrade head"
    
    # 启动应用
    ssh $server "sudo systemctl start chronoretrace"
    
    # 健康检查
    if health_check $server; then
        # 重新加入负载均衡器
        nginx_add_server $server
        echo "$server upgraded successfully"
    else
        echo "$server upgrade failed, rolling back..."
        rollback $server
        exit 1
    fi
    
    sleep 10
done

echo "Rolling upgrade completed"
```

### 2. 数据库升级

#### 迁移脚本

```bash
#!/bin/bash
# db_migrate.sh

echo "Starting database migration..."

# 备份当前数据库
pg_dump chronoretrace_db > backup_before_migration.sql

# 运行迁移
alembic upgrade head

# 验证迁移
psql -d chronoretrace_db -c "SELECT version_num FROM alembic_version;"

echo "Database migration completed"
```

### 3. 配置更新

#### 配置热更新

```python
# 支持配置热更新的代码示例
import signal
import yaml

class ConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = self.load_config()
        signal.signal(signal.SIGHUP, self.reload_config)
    
    def load_config(self):
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def reload_config(self, signum, frame):
        print("Reloading configuration...")
        self.config = self.load_config()
        print("Configuration reloaded")

# 使用方法
config_manager = ConfigManager('config/performance.yaml')

# 发送 SIGHUP 信号重新加载配置
# kill -HUP <pid>
```

## 安全建议

### 1. 网络安全

- 使用防火墙限制访问端口
- 启用 HTTPS/TLS 加密
- 配置 VPN 访问内部服务
- 定期更新 SSL 证书

### 2. 应用安全

- 定期更新依赖包
- 使用强密码和密钥
- 启用访问日志审计
- 实施 API 限流和认证

### 3. 数据安全

- 加密敏感数据
- 定期备份验证
- 实施访问控制
- 监控异常访问

---

本文档将随着系统的发展持续更新。如有问题，请联系运维团队。