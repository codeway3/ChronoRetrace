# Docker 部署指南

本文档详细介绍如何使用 Docker 和 Docker Compose 部署 ChronoRetrace 应用。

## 目录

- [Docker 环境准备](#docker-环境准备)
- [镜像构建](#镜像构建)
- [容器配置](#容器配置)
- [网络配置](#网络配置)
- [存储配置](#存储配置)
- [环境变量](#环境变量)
- [服务编排](#服务编排)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)

## Docker 环境准备

### 安装 Docker

#### Ubuntu/Debian
```bash
# 更新包索引
sudo apt-get update

# 安装依赖
sudo apt-get install apt-transport-https ca-certificates curl gnupg lsb-release

# 添加 Docker GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.12.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### macOS
```bash
# 使用 Homebrew 安装
brew install docker docker-compose

# 或下载 Docker Desktop
# https://www.docker.com/products/docker-desktop
```

#### Windows
```powershell
# 下载并安装 Docker Desktop
# https://www.docker.com/products/docker-desktop

# 或使用 Chocolatey
choco install docker-desktop
```

### 验证安装
```bash
# 检查 Docker 版本
docker --version
docker-compose --version

# 测试 Docker 运行
docker run hello-world
```

## 镜像构建

### 后端镜像构建
```bash
# 进入后端目录
cd backend

# 构建开发镜像
docker build -t chronoretrace-backend:dev -f Dockerfile.dev .

# 构建生产镜像
docker build -t chronoretrace-backend:latest .

# 多阶段构建优化
docker build --target production -t chronoretrace-backend:prod .
```

### 前端镜像构建
```bash
# 进入前端目录
cd frontend

# 构建开发镜像
docker build -t chronoretrace-frontend:dev -f Dockerfile.dev .

# 构建生产镜像
docker build -t chronoretrace-frontend:latest .
```

### 镜像优化
```dockerfile
# 使用多阶段构建减小镜像大小
FROM node:16-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:16-alpine AS runtime
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

### 镜像标签管理
```bash
# 标签版本
docker tag chronoretrace-backend:latest chronoretrace-backend:v1.0.0

# 推送到仓库
docker push chronoretrace-backend:v1.0.0

# 清理未使用的镜像
docker image prune -f
```

## 容器配置

### 资源限制
```yaml
# docker-compose.yml
services:
  backend:
    image: chronoretrace-backend:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    restart: unless-stopped
```

### 健康检查
```yaml
services:
  backend:
    image: chronoretrace-backend:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 安全配置
```yaml
services:
  backend:
    image: chronoretrace-backend:latest
    user: "1000:1000"  # 非 root 用户
    read_only: true     # 只读文件系统
    tmpfs:
      - /tmp
      - /var/tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

## 网络配置

### 自定义网络
```yaml
networks:
  chronoretrace-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1

services:
  backend:
    networks:
      - chronoretrace-network
  frontend:
    networks:
      - chronoretrace-network
```

### 端口映射
```yaml
services:
  backend:
    ports:
      - "8000:8000"      # HTTP
      - "8443:8443"      # HTTPS
  frontend:
    ports:
      - "3000:3000"      # 开发环境
      - "80:80"          # 生产环境
      - "443:443"        # HTTPS
```

### 服务发现
```yaml
services:
  backend:
    hostname: chronoretrace-backend
    aliases:
      - api
      - backend-service
  postgres:
    hostname: chronoretrace-db
    aliases:
      - database
      - db
```

## 存储配置

### 数据卷管理
```yaml
volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  app_logs:
    driver: local

services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro

  backend:
    volumes:
      - app_logs:/app/logs
      - ./config:/app/config:ro
```

### 绑定挂载
```yaml
services:
  backend:
    volumes:
      - ./backend:/app                    # 开发环境代码挂载
      - ./logs:/app/logs                  # 日志目录
      - ./config/app.conf:/app/config/app.conf:ro  # 配置文件
```

### 临时文件系统
```yaml
services:
  backend:
    tmpfs:
      - /tmp:size=100M,noexec,nosuid,nodev
      - /var/tmp:size=50M,noexec,nosuid,nodev
```

## 环境变量

### 环境文件
```bash
# .env
DATABASE_URL=postgresql://chronoretrace:password@postgres:5432/chronoretrace
REDIS_URL=redis://redis:6379/0
JWT_SECRET=your-jwt-secret-key
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
```

### 敏感信息管理
```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - DATABASE_URL_FILE=/run/secrets/db_url
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
    secrets:
      - db_url
      - jwt_secret

secrets:
  db_url:
    file: ./secrets/database_url.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

### 环境特定配置
```yaml
# docker-compose.override.yml (开发环境)
services:
  backend:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
    volumes:
      - ./backend:/app
    command: python manage.py runserver 0.0.0.0:8000
```

## 服务编排

### 完整的 docker-compose.yml
```yaml
version: '3.8'

services:
  # 数据库服务
  postgres:
    image: postgres:13-alpine
    environment:
      POSTGRES_DB: chronoretrace
      POSTGRES_USER: chronoretrace
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chronoretrace"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis 缓存
  redis:
    image: redis:6-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    restart: unless-stopped

  # 后端服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://chronoretrace:${POSTGRES_PASSWORD}@postgres:5432/chronoretrace
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    name: chronoretrace-network
```

### 服务启动顺序
```yaml
services:
  backend:
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    restart: on-failure:3
```

## 监控和日志

### 日志配置
```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=backend"
```

### 监控集成
```yaml
services:
  # Prometheus 监控
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  # Grafana 可视化
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
```

### 日志聚合
```yaml
services:
  # ELK Stack
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:7.15.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline:ro

  kibana:
    image: docker.elastic.co/kibana/kibana:7.15.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

## 故障排除

### 常用调试命令
```bash
# 查看容器状态
docker-compose ps

# 查看容器日志
docker-compose logs -f backend

# 进入容器调试
docker-compose exec backend bash

# 检查网络连接
docker-compose exec backend ping postgres

# 查看资源使用
docker stats

# 检查容器配置
docker inspect chronoretrace_backend_1
```

### 常见问题解决

#### 1. 容器无法启动
```bash
# 检查镜像是否存在
docker images

# 重新构建镜像
docker-compose build --no-cache

# 检查端口占用
netstat -tulpn | grep :8000
```

#### 2. 数据库连接失败
```bash
# 检查数据库容器状态
docker-compose exec postgres pg_isready

# 测试数据库连接
docker-compose exec postgres psql -U chronoretrace -d chronoretrace

# 检查网络连通性
docker-compose exec backend nslookup postgres
```

#### 3. 性能问题
```bash
# 监控资源使用
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 检查磁盘使用
docker system df

# 清理未使用资源
docker system prune -f
```

### 备份和恢复
```bash
# 备份数据库
docker-compose exec postgres pg_dump -U chronoretrace chronoretrace > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U chronoretrace chronoretrace < backup.sql

# 备份数据卷
docker run --rm -v chronoretrace_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# 恢复数据卷
docker run --rm -v chronoretrace_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

## 生产环境最佳实践

### 安全配置
```yaml
services:
  backend:
    # 使用非 root 用户
    user: "1000:1000"

    # 只读文件系统
    read_only: true
    tmpfs:
      - /tmp

    # 限制能力
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE

    # 安全选项
    security_opt:
      - no-new-privileges:true
```

### 资源管理
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

### 高可用配置
```yaml
services:
  backend:
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      rollback_config:
        parallelism: 1
        delay: 5s
```

这个 Docker 部署指南提供了从基础安装到生产环境部署的完整流程，包括最佳实践和故障排除方法。
