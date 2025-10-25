# ChronoRetrace 部署指南

本文档提供了 ChronoRetrace 应用的完整部署指南，包括开发环境、测试环境和生产环境的部署方案。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [部署方式](#部署方式)
- [监控和运维](#监控和运维)
- [故障排除](#故障排除)
- [安全配置](#安全配置)

## 系统要求

### 最低配置
- CPU: 2 核心
- 内存: 4GB RAM
- 存储: 20GB 可用空间
- 操作系统: Linux (Ubuntu 20.04+), macOS, Windows 10+

### 推荐配置（生产环境）
- CPU: 4+ 核心
- 内存: 8GB+ RAM
- 存储: 100GB+ SSD
- 网络: 1Gbps+

### 依赖软件
- Python 3.10（必须）
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.20+ (生产环境)
- PostgreSQL 13+ (生产环境)
- Redis 6.0+ (生产环境)

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/codeway3/ChronoRetrace.git
cd ChronoRetrace
```

### 2. 环境配置
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

### 3. 启动开发环境
```bash
# 使用 Docker Compose 启动
docker-compose up -d

# 或使用部署脚本
python scripts/deploy.py --environment development
```

### 4. 验证部署
```bash
# 检查服务状态
docker-compose ps

# 访问应用
open http://localhost:3000
```

## 环境配置

### 开发环境
开发环境使用 Docker Compose 进行本地开发和测试。

```bash
# 启动开发环境
docker-compose -f docker-compose.dev.yml up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 测试环境
测试环境模拟生产环境配置，用于集成测试和性能测试。

```bash
# 部署到测试环境
python scripts/deploy.py --environment testing

# 运行测试
python scripts/performance_test.py --environment testing
```

### 生产环境
生产环境使用 Kubernetes 进行容器编排和管理。

```bash
# 部署到生产环境
python scripts/deployment_automation.py --environment production

# 监控部署状态
kubectl get pods -n chronoretrace
```

## 部署方式

### Docker Compose 部署
适用于开发和小规模部署。

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 扩展服务
docker-compose up -d --scale backend=3
```

### Kubernetes 部署
适用于生产环境和大规模部署。

```bash
# 应用配置
kubectl apply -f k8s/

# 检查部署状态
kubectl rollout status deployment/chronoretrace-backend

# 查看服务
kubectl get services
```

### 自动化部署
使用 CI/CD 流水线进行自动化部署。

```bash
# 触发部署
git push origin main

# 监控部署
gh workflow view
```

## 监控和运维

### 监控系统
- **Prometheus**: 指标收集和存储
- **Grafana**: 可视化监控面板
- **Alertmanager**: 告警管理

```bash
# 部署监控系统
python backend/scripts/deploy_monitoring.py

# 访问监控面板
open http://localhost:3001  # Grafana
open http://localhost:9090  # Prometheus
```

### 健康检查
```bash
# 运行健康检查
python backend/scripts/monitoring_health_check.py

# 检查特定服务
curl http://localhost:8000/health
```

### 日志管理
```bash
# 查看应用日志
kubectl logs -f deployment/chronoretrace-backend

# 查看系统日志
journalctl -u docker
```

## 故障排除

### 常见问题

#### 1. 容器启动失败
```bash
# 检查容器状态
docker ps -a

# 查看容器日志
docker logs <container_id>

# 检查资源使用
docker stats
```

#### 2. 数据库连接问题
```bash
# 检查数据库状态
docker-compose exec postgres psql -U chronoretrace -c "\l"

# 测试连接
psql -h localhost -U chronoretrace -d chronoretrace
```

#### 3. 网络问题
```bash
# 检查网络配置
docker network ls

# 测试网络连通性
docker-compose exec backend ping postgres
```

#### 4. 性能问题
```bash
# 运行性能测试
python scripts/performance_test.py

# 检查资源使用
kubectl top pods
```

### 调试工具

```bash
# 进入容器调试
docker-compose exec backend bash

# 查看配置
kubectl describe pod <pod_name>

# 检查事件
kubectl get events --sort-by=.metadata.creationTimestamp
```

## 安全配置

### 网络安全
- 使用 HTTPS/TLS 加密
- 配置防火墙规则
- 限制网络访问

### 认证和授权
- JWT 令牌认证
- RBAC 权限控制
- API 密钥管理

### 数据安全
- 数据库加密
- 敏感信息脱敏
- 定期备份

```bash
# 生成 SSL 证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout tls.key -out tls.crt

# 创建 Kubernetes Secret
kubectl create secret tls chronoretrace-tls \
  --cert=tls.crt --key=tls.key
```

## 备份和恢复

### 数据库备份
```bash
# 创建备份
pg_dump -h localhost -U chronoretrace chronoretrace > backup.sql

# 恢复备份
psql -h localhost -U chronoretrace chronoretrace < backup.sql
```

### 配置备份
```bash
# 备份 Kubernetes 配置
kubectl get all -o yaml > k8s-backup.yaml

# 备份环境配置
cp .env .env.backup
```

## 扩展和优化

### 水平扩展
```bash
# Kubernetes 自动扩展
kubectl autoscale deployment chronoretrace-backend \
  --cpu-percent=70 --min=2 --max=10

# Docker Compose 手动扩展
docker-compose up -d --scale backend=5
```

### 性能优化
- 数据库索引优化
- 缓存策略配置
- CDN 配置
- 负载均衡优化

## 联系支持

如果遇到问题，请通过以下方式获取支持：

- 📧 邮箱: support@chronoretrace.com
- 📱 电话: +86-xxx-xxxx-xxxx
- 💬 Slack: #chronoretrace-support
- 🐛 问题反馈: [GitHub Issues](https://github.com/codeway3/ChronoRetrace/issues)

## 更新日志

查看 [CHANGELOG.md](../CHANGELOG.md) 了解版本更新信息。

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](../LICENSE) 文件。
