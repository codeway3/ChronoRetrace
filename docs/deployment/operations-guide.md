# ChronoRetrace 运维指南

本文档提供 ChronoRetrace 应用的日常运维操作指南，包括监控、维护、故障处理和性能优化等内容。

## 目录

- [日常监控](#日常监控)
- [健康检查](#健康检查)
- [日志管理](#日志管理)
- [备份策略](#备份策略)
- [性能优化](#性能优化)
- [安全维护](#安全维护)
- [故障处理](#故障处理)
- [容量规划](#容量规划)
- [升级维护](#升级维护)
- [应急响应](#应急响应)

## 日常监控

### 监控指标

#### 应用层指标
- **响应时间**: API 平均响应时间 < 200ms
- **错误率**: 4xx/5xx 错误率 < 1%
- **吞吐量**: 每秒请求数 (RPS)
- **可用性**: 服务可用性 > 99.9%

#### 系统层指标
- **CPU 使用率**: < 70%
- **内存使用率**: < 80%
- **磁盘使用率**: < 85%
- **网络 I/O**: 带宽使用情况

#### 数据库指标
- **连接数**: 活跃连接数
- **查询性能**: 慢查询监控
- **锁等待**: 锁等待时间
- **复制延迟**: 主从复制延迟

### 监控工具配置

#### Prometheus 查询示例
```promql
# API 响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 错误率
rate(http_requests_total{status=~"4..|5.."}[5m]) / rate(http_requests_total[5m])

# CPU 使用率
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 磁盘使用率
100 - ((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes)
```

#### Grafana 仪表板
```json
{
  "dashboard": {
    "title": "ChronoRetrace 监控仪表板",
    "panels": [
      {
        "title": "API 响应时间",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "错误率",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"4..|5..\"}[5m]) / rate(http_requests_total[5m])"
          }
        ]
      }
    ]
  }
}
```

### 告警规则

#### Prometheus 告警规则
```yaml
# alerts.yml
groups:
- name: chronoretrace.rules
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} for the last 5 minutes"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }}s"

  - alert: HighCPUUsage
    expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage"
      description: "CPU usage is {{ $value }}% on {{ $labels.instance }}"

  - alert: HighMemoryUsage
    expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value }}% on {{ $labels.instance }}"

  - alert: DiskSpaceLow
    expr: 100 - ((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes) > 90
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Disk space low"
      description: "Disk usage is {{ $value }}% on {{ $labels.instance }}"

  - alert: ServiceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service is down"
      description: "{{ $labels.instance }} has been down for more than 1 minute"
```

## 健康检查

### 自动化健康检查
```bash
#!/bin/bash
# health_check.sh

set -e

CHECK_INTERVAL=60  # 检查间隔（秒）
LOG_FILE="/var/log/chronoretrace/health_check.log"

# 检查 API 健康状态
check_api_health() {
    local endpoint="$1"
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$endpoint/health")
    
    if [ "$response" = "200" ]; then
        echo "$(date): API health check passed - $endpoint" >> "$LOG_FILE"
        return 0
    else
        echo "$(date): API health check failed - $endpoint (HTTP $response)" >> "$LOG_FILE"
        return 1
    fi
}

# 检查数据库连接
check_database() {
    local db_host="$1"
    local db_port="$2"
    local db_user="$3"
    local db_name="$4"
    
    if pg_isready -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" > /dev/null 2>&1; then
        echo "$(date): Database health check passed" >> "$LOG_FILE"
        return 0
    else
        echo "$(date): Database health check failed" >> "$LOG_FILE"
        return 1
    fi
}

# 检查 Redis 连接
check_redis() {
    local redis_host="$1"
    local redis_port="$2"
    
    if redis-cli -h "$redis_host" -p "$redis_port" ping > /dev/null 2>&1; then
        echo "$(date): Redis health check passed" >> "$LOG_FILE"
        return 0
    else
        echo "$(date): Redis health check failed" >> "$LOG_FILE"
        return 1
    fi
}

# 主检查循环
while true; do
    echo "$(date): Starting health checks..." >> "$LOG_FILE"
    
    # 检查各个组件
    check_api_health "http://localhost:8000" || echo "API check failed"
    check_database "localhost" "5432" "chronoretrace" "chronoretrace" || echo "Database check failed"
    check_redis "localhost" "6379" || echo "Redis check failed"
    
    sleep "$CHECK_INTERVAL"
done
```

### Kubernetes 健康检查
```bash
#!/bin/bash
# k8s_health_check.sh

NAMESPACE="chronoretrace"

# 检查 Pod 状态
echo "Checking Pod status..."
kubectl get pods -n "$NAMESPACE" --no-headers | while read line; do
    pod_name=$(echo $line | awk '{print $1}')
    status=$(echo $line | awk '{print $3}')
    ready=$(echo $line | awk '{print $2}')
    
    if [ "$status" != "Running" ]; then
        echo "WARNING: Pod $pod_name is not running (Status: $status)"
    fi
    
    if [[ "$ready" != *"/"* ]] || [[ "$ready" == *"0/"* ]]; then
        echo "WARNING: Pod $pod_name is not ready (Ready: $ready)"
    fi
done

# 检查服务端点
echo "Checking Service endpoints..."
kubectl get endpoints -n "$NAMESPACE" --no-headers | while read line; do
    service_name=$(echo $line | awk '{print $1}')
    endpoints=$(echo $line | awk '{print $2}')
    
    if [ "$endpoints" = "<none>" ]; then
        echo "WARNING: Service $service_name has no endpoints"
    fi
done

# 检查 PVC 状态
echo "Checking PVC status..."
kubectl get pvc -n "$NAMESPACE" --no-headers | while read line; do
    pvc_name=$(echo $line | awk '{print $1}')
    status=$(echo $line | awk '{print $2}')
    
    if [ "$status" != "Bound" ]; then
        echo "WARNING: PVC $pvc_name is not bound (Status: $status)"
    fi
done
```

## 日志管理

### 日志收集配置

#### Fluentd 配置
```ruby
# fluent.conf
<source>
  @type tail
  path /var/log/chronoretrace/*.log
  pos_file /var/log/fluentd-chronoretrace.log.pos
  tag chronoretrace.*
  format json
  time_format %Y-%m-%dT%H:%M:%S.%NZ
</source>

<filter chronoretrace.**>
  @type record_transformer
  <record>
    hostname "#{Socket.gethostname}"
    environment "#{ENV['ENVIRONMENT'] || 'production'}"
  </record>
</filter>

<match chronoretrace.**>
  @type elasticsearch
  host elasticsearch.logging.svc.cluster.local
  port 9200
  index_name chronoretrace-${tag_parts[1]}
  type_name _doc
  
  <buffer>
    @type file
    path /var/log/fluentd-buffers/chronoretrace
    flush_mode interval
    flush_interval 10s
    chunk_limit_size 2M
    queue_limit_length 32
  </buffer>
</match>
```

#### Logrotate 配置
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

### 日志分析

#### 常用日志查询
```bash
# 查看错误日志
grep -i error /var/log/chronoretrace/app.log | tail -100

# 查看慢查询
grep "slow query" /var/log/chronoretrace/database.log

# 统计 API 调用
awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -nr

# 查看特定时间段的日志
sed -n '/2023-12-01 10:00:00/,/2023-12-01 11:00:00/p' /var/log/chronoretrace/app.log
```

#### ELK 查询示例
```json
{
  "query": {
    "bool": {
      "must": [
        {
          "range": {
            "@timestamp": {
              "gte": "now-1h",
              "lte": "now"
            }
          }
        },
        {
          "term": {
            "level": "ERROR"
          }
        }
      ]
    }
  },
  "sort": [
    {
      "@timestamp": {
        "order": "desc"
      }
    }
  ]
}
```

## 备份策略

### 数据库备份

#### 自动备份脚本
```bash
#!/bin/bash
# backup_database.sh

set -e

DB_HOST="localhost"
DB_PORT="5432"
DB_USER="chronoretrace"
DB_NAME="chronoretrace"
BACKUP_DIR="/backup/database"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名
BACKUP_FILE="$BACKUP_DIR/chronoretrace_$(date +%Y%m%d_%H%M%S).sql"

# 执行备份
echo "Starting database backup..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"

# 压缩备份文件
gzip "$BACKUP_FILE"

# 删除过期备份
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

echo "Database backup completed: ${BACKUP_FILE}.gz"
```

#### Kubernetes 备份
```bash
#!/bin/bash
# k8s_backup_database.sh

NAMESPACE="chronoretrace"
POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app=chronoretrace-postgres -o jsonpath='{.items[0].metadata.name}')
BACKUP_DIR="/backup/k8s"

mkdir -p "$BACKUP_DIR"

# 执行数据库备份
BACKUP_FILE="$BACKUP_DIR/chronoretrace_$(date +%Y%m%d_%H%M%S).sql"
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- pg_dump -U chronoretrace chronoretrace > "$BACKUP_FILE"

# 压缩备份
gzip "$BACKUP_FILE"

echo "Kubernetes database backup completed: ${BACKUP_FILE}.gz"
```

### 配置备份
```bash
#!/bin/bash
# backup_config.sh

BACKUP_DIR="/backup/config"
CONFIG_DIRS=(
    "/etc/chronoretrace"
    "/opt/chronoretrace/config"
    "$HOME/.chronoretrace"
)

mkdir -p "$BACKUP_DIR"

# 备份配置文件
for dir in "${CONFIG_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        tar -czf "$BACKUP_DIR/config_$(basename $dir)_$(date +%Y%m%d).tar.gz" -C "$(dirname $dir)" "$(basename $dir)"
    fi
done

# Kubernetes 配置备份
kubectl get all,configmap,secret,pvc -n chronoretrace -o yaml > "$BACKUP_DIR/k8s_config_$(date +%Y%m%d).yaml"

echo "Configuration backup completed"
```

### 备份验证
```bash
#!/bin/bash
# verify_backup.sh

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 验证备份文件完整性
if [ "${BACKUP_FILE##*.}" = "gz" ]; then
    if gzip -t "$BACKUP_FILE"; then
        echo "Backup file integrity check passed"
    else
        echo "Backup file is corrupted"
        exit 1
    fi
fi

# 验证 SQL 备份内容
if [[ "$BACKUP_FILE" == *.sql* ]]; then
    if zcat "$BACKUP_FILE" 2>/dev/null | head -10 | grep -q "PostgreSQL database dump"; then
        echo "SQL backup format validation passed"
    else
        echo "Invalid SQL backup format"
        exit 1
    fi
fi

echo "Backup verification completed successfully"
```

## 性能优化

### 数据库优化

#### PostgreSQL 配置优化
```sql
-- postgresql.conf 优化建议

-- 内存配置
shared_buffers = 256MB                    -- 25% of RAM
effective_cache_size = 1GB                -- 75% of RAM
work_mem = 4MB                            -- Per connection
maintenance_work_mem = 64MB               -- For maintenance operations

-- 连接配置
max_connections = 100                     -- 根据实际需求调整

-- 检查点配置
checkpoint_completion_target = 0.9
wal_buffers = 16MB

-- 查询优化
random_page_cost = 1.1                   -- SSD 存储
effective_io_concurrency = 200            -- SSD 存储

-- 日志配置
log_min_duration_statement = 1000         -- 记录慢查询
log_checkpoints = on
log_connections = on
log_disconnections = on
```

#### 索引优化
```sql
-- 分析查询性能
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM users WHERE email = 'user@example.com';

-- 创建复合索引
CREATE INDEX CONCURRENTLY idx_users_email_status ON users(email, status);

-- 创建部分索引
CREATE INDEX CONCURRENTLY idx_active_users ON users(created_at) WHERE status = 'active';

-- 分析表统计信息
ANALYZE users;

-- 查看索引使用情况
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### 应用层优化

#### 缓存策略
```python
# Redis 缓存配置
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# 使用示例
@cache_result(expiration=1800)
def get_user_profile(user_id):
    # 数据库查询逻辑
    pass
```

#### 连接池优化
```python
# 数据库连接池配置
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:password@localhost/dbname',
    poolclass=QueuePool,
    pool_size=20,                    # 连接池大小
    max_overflow=30,                 # 最大溢出连接数
    pool_pre_ping=True,              # 连接前检查
    pool_recycle=3600,               # 连接回收时间
    echo=False                       # 生产环境关闭 SQL 日志
)
```

### 系统层优化

#### 内核参数优化
```bash
# /etc/sysctl.conf

# 网络优化
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 5000

# 内存优化
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# 文件系统优化
fs.file-max = 65535
fs.nr_open = 1048576

# 应用生效
sysctl -p
```

#### 文件描述符限制
```bash
# /etc/security/limits.conf
chronoretrace soft nofile 65535
chronoretrace hard nofile 65535
chronoretrace soft nproc 32768
chronoretrace hard nproc 32768
```

## 安全维护

### 安全检查清单

#### 定期安全检查
```bash
#!/bin/bash
# security_check.sh

echo "=== ChronoRetrace 安全检查 ==="

# 检查系统更新
echo "检查系统更新..."
apt list --upgradable 2>/dev/null | grep -v "WARNING" | wc -l

# 检查开放端口
echo "检查开放端口..."
netstat -tulpn | grep LISTEN

# 检查失败登录尝试
echo "检查失败登录尝试..."
grep "Failed password" /var/log/auth.log | tail -10

# 检查文件权限
echo "检查关键文件权限..."
find /etc/chronoretrace -type f -perm /o+w -ls

# 检查 SSL 证书有效期
echo "检查 SSL 证书..."
openssl x509 -in /etc/ssl/certs/chronoretrace.crt -noout -dates

# 检查数据库用户权限
echo "检查数据库权限..."
psql -U postgres -c "\du"
```

#### 漏洞扫描
```bash
#!/bin/bash
# vulnerability_scan.sh

# 使用 Lynis 进行系统安全审计
lynis audit system

# 使用 OWASP ZAP 进行 Web 应用扫描
zap-cli quick-scan --self-contained http://localhost:8000

# 使用 Nmap 进行端口扫描
nmap -sS -O localhost

# 检查 Docker 镜像漏洞
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image chronoretrace-backend:latest
```

### 访问控制

#### 防火墙配置
```bash
#!/bin/bash
# firewall_setup.sh

# 清除现有规则
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# 设置默认策略
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 允许本地回环
iptables -A INPUT -i lo -j ACCEPT

# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 允许 SSH (限制源 IP)
iptables -A INPUT -p tcp --dport 22 -s 192.168.1.0/24 -j ACCEPT

# 允许 HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许应用端口 (限制源)
iptables -A INPUT -p tcp --dport 8000 -s 10.0.0.0/8 -j ACCEPT

# 保存规则
iptables-save > /etc/iptables/rules.v4
```

## 故障处理

### 故障分类和处理流程

#### P0 - 严重故障（服务完全不可用）
1. **立即响应**（5分钟内）
2. **建立事故指挥**
3. **快速诊断和修复**
4. **服务恢复验证**
5. **事后分析**

#### P1 - 高优先级故障（核心功能受影响）
1. **30分钟内响应**
2. **影响评估**
3. **制定修复计划**
4. **实施修复**
5. **功能验证**

#### P2 - 中等优先级故障（部分功能受影响）
1. **2小时内响应**
2. **问题分析**
3. **计划修复时间**
4. **实施修复**

### 常见故障处理

#### 服务无响应
```bash
#!/bin/bash
# service_recovery.sh

SERVICE_NAME="chronoretrace-backend"
HEALTH_URL="http://localhost:8000/health"

# 检查服务状态
if ! curl -f "$HEALTH_URL" > /dev/null 2>&1; then
    echo "Service is not responding, attempting recovery..."
    
    # 检查进程
    if pgrep -f "$SERVICE_NAME" > /dev/null; then
        echo "Process exists, checking resources..."
        
        # 检查内存使用
        MEMORY_USAGE=$(ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem -C python | head -2 | tail -1 | awk '{print $4}')
        if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
            echo "High memory usage detected, restarting service..."
            systemctl restart "$SERVICE_NAME"
        fi
        
        # 检查 CPU 使用
        CPU_USAGE=$(ps -o pid,ppid,cmd,%mem,%cpu --sort=-%cpu -C python | head -2 | tail -1 | awk '{print $5}')
        if (( $(echo "$CPU_USAGE > 95" | bc -l) )); then
            echo "High CPU usage detected, restarting service..."
            systemctl restart "$SERVICE_NAME"
        fi
    else
        echo "Process not found, starting service..."
        systemctl start "$SERVICE_NAME"
    fi
    
    # 等待服务启动
    sleep 30
    
    # 验证恢复
    if curl -f "$HEALTH_URL" > /dev/null 2>&1; then
        echo "Service recovery successful"
    else
        echo "Service recovery failed, escalating..."
        # 发送告警
    fi
fi
```

#### 数据库连接问题
```bash
#!/bin/bash
# database_recovery.sh

DB_HOST="localhost"
DB_PORT="5432"
DB_USER="chronoretrace"

# 检查数据库连接
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    echo "Database connection failed, checking..."
    
    # 检查 PostgreSQL 服务
    if ! systemctl is-active postgresql > /dev/null 2>&1; then
        echo "PostgreSQL service is not running, starting..."
        systemctl start postgresql
        sleep 10
    fi
    
    # 检查连接数
    CONNECTIONS=$(psql -h "$DB_HOST" -U postgres -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null || echo "0")
    MAX_CONNECTIONS=$(psql -h "$DB_HOST" -U postgres -t -c "SHOW max_connections;" 2>/dev/null || echo "100")
    
    if [ "$CONNECTIONS" -ge "$MAX_CONNECTIONS" ]; then
        echo "Too many connections, terminating idle connections..."
        psql -h "$DB_HOST" -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '1 hour';"
    fi
    
    # 检查磁盘空间
    DISK_USAGE=$(df /var/lib/postgresql | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        echo "Disk space critical, cleaning up..."
        # 清理日志文件
        find /var/lib/postgresql -name "*.log" -mtime +7 -delete
    fi
fi
```

## 容量规划

### 资源监控和预测

#### 容量监控脚本
```bash
#!/bin/bash
# capacity_monitoring.sh

LOG_FILE="/var/log/chronoretrace/capacity.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# CPU 使用率
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')

# 内存使用率
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')

# 磁盘使用率
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')

# 网络流量
NETWORK_IN=$(cat /proc/net/dev | grep eth0 | awk '{print $2}')
NETWORK_OUT=$(cat /proc/net/dev | grep eth0 | awk '{print $10}')

# 数据库连接数
DB_CONNECTIONS=$(psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null || echo "0")

# 记录到日志
echo "$DATE,CPU:$CPU_USAGE,Memory:$MEMORY_USAGE,Disk:$DISK_USAGE,DB_Conn:$DB_CONNECTIONS,Net_In:$NETWORK_IN,Net_Out:$NETWORK_OUT" >> "$LOG_FILE"

# 检查阈值并告警
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
    echo "WARNING: High CPU usage: $CPU_USAGE%"
fi

if (( $(echo "$MEMORY_USAGE > 85" | bc -l) )); then
    echo "WARNING: High memory usage: $MEMORY_USAGE%"
fi

if [ "$DISK_USAGE" -gt 85 ]; then
    echo "WARNING: High disk usage: $DISK_USAGE%"
fi
```

### 扩容策略

#### 水平扩容
```bash
#!/bin/bash
# horizontal_scaling.sh

CURRENT_REPLICAS=$(kubectl get deployment chronoretrace-backend -o jsonpath='{.spec.replicas}')
CPU_USAGE=$(kubectl top pods -l app=chronoretrace-backend --no-headers | awk '{sum+=$3} END {print sum/NR}' | sed 's/m//')

# 如果 CPU 使用率超过 70%，增加副本
if [ "$CPU_USAGE" -gt 700 ]; then
    NEW_REPLICAS=$((CURRENT_REPLICAS + 1))
    if [ "$NEW_REPLICAS" -le 10 ]; then
        echo "Scaling up to $NEW_REPLICAS replicas"
        kubectl scale deployment chronoretrace-backend --replicas="$NEW_REPLICAS"
    fi
fi

# 如果 CPU 使用率低于 30%，减少副本
if [ "$CPU_USAGE" -lt 300 ] && [ "$CURRENT_REPLICAS" -gt 2 ]; then
    NEW_REPLICAS=$((CURRENT_REPLICAS - 1))
    echo "Scaling down to $NEW_REPLICAS replicas"
    kubectl scale deployment chronoretrace-backend --replicas="$NEW_REPLICAS"
fi
```

#### 垂直扩容
```yaml
# vertical-scaling.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: chronoretrace-backend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: chronoretrace-backend
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: backend
      maxAllowed:
        cpu: 2
        memory: 4Gi
      minAllowed:
        cpu: 100m
        memory: 128Mi
```

## 升级维护

### 滚动升级策略

#### Kubernetes 滚动升级
```bash
#!/bin/bash
# rolling_update.sh

NEW_IMAGE="$1"
NAMESPACE="chronoretrace"

if [ -z "$NEW_IMAGE" ]; then
    echo "Usage: $0 <new_image>"
    exit 1
fi

echo "Starting rolling update to $NEW_IMAGE..."

# 更新镜像
kubectl set image deployment/chronoretrace-backend backend="$NEW_IMAGE" -n "$NAMESPACE"

# 等待滚动更新完成
kubectl rollout status deployment/chronoretrace-backend -n "$NAMESPACE" --timeout=600s

# 验证更新
if kubectl rollout status deployment/chronoretrace-backend -n "$NAMESPACE" | grep -q "successfully rolled out"; then
    echo "Rolling update completed successfully"
    
    # 运行健康检查
    sleep 30
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "Health check passed"
    else
        echo "Health check failed, rolling back..."
        kubectl rollout undo deployment/chronoretrace-backend -n "$NAMESPACE"
        exit 1
    fi
else
    echo "Rolling update failed"
    exit 1
fi
```

### 数据库迁移

#### 安全迁移流程
```bash
#!/bin/bash
# database_migration.sh

MIGRATION_FILE="$1"
BACKUP_DIR="/backup/pre-migration"

if [ -z "$MIGRATION_FILE" ]; then
    echo "Usage: $0 <migration_file>"
    exit 1
fi

# 创建备份
echo "Creating pre-migration backup..."
mkdir -p "$BACKUP_DIR"
pg_dump -U chronoretrace chronoretrace > "$BACKUP_DIR/pre_migration_$(date +%Y%m%d_%H%M%S).sql"

# 验证迁移文件
echo "Validating migration file..."
if ! psql -U chronoretrace -d chronoretrace --dry-run -f "$MIGRATION_FILE" > /dev/null 2>&1; then
    echo "Migration file validation failed"
    exit 1
fi

# 执行迁移
echo "Executing migration..."
psql -U chronoretrace -d chronoretrace -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo "Migration completed successfully"
    
    # 验证数据完整性
    echo "Verifying data integrity..."
    psql -U chronoretrace -d chronoretrace -c "SELECT COUNT(*) FROM users;"
    
else
    echo "Migration failed, restoring backup..."
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*.sql | head -1)
    psql -U chronoretrace -d chronoretrace < "$LATEST_BACKUP"
    exit 1
fi
```

## 应急响应

### 应急响应计划

#### 事故响应流程
1. **事故检测**（自动监控 + 人工发现）
2. **事故分类**（P0/P1/P2）
3. **应急小组激活**
4. **影响评估**
5. **应急处理**
6. **服务恢复**
7. **事后分析**

#### 应急联系人
```yaml
# emergency_contacts.yaml
contacts:
  - role: "技术负责人"
    name: "张三"
    phone: "+86-138-0000-0001"
    email: "zhang.san@company.com"
    
  - role: "运维工程师"
    name: "李四"
    phone: "+86-138-0000-0002"
    email: "li.si@company.com"
    
  - role: "数据库管理员"
    name: "王五"
    phone: "+86-138-0000-0003"
    email: "wang.wu@company.com"

escalation:
  - level: 1
    timeout: 15  # 分钟
    contacts: ["运维工程师"]
    
  - level: 2
    timeout: 30
    contacts: ["技术负责人", "数据库管理员"]
    
  - level: 3
    timeout: 60
    contacts: ["所有人"]
```

#### 应急脚本
```bash
#!/bin/bash
# emergency_response.sh

INCIDENT_TYPE="$1"
SEVERITY="$2"

case "$INCIDENT_TYPE" in
    "service_down")
        echo "Service down detected, executing recovery..."
        systemctl restart chronoretrace-backend
        systemctl restart chronoretrace-frontend
        ;;
        
    "database_down")
        echo "Database down detected, executing recovery..."
        systemctl restart postgresql
        sleep 30
        # 验证数据库恢复
        pg_isready -h localhost -p 5432
        ;;
        
    "high_load")
        echo "High load detected, scaling up..."
        kubectl scale deployment chronoretrace-backend --replicas=5
        ;;
        
    "disk_full")
        echo "Disk full detected, cleaning up..."
        # 清理临时文件
        find /tmp -type f -mtime +1 -delete
        # 清理日志文件
        find /var/log -name "*.log" -mtime +7 -delete
        ;;
        
    *)
        echo "Unknown incident type: $INCIDENT_TYPE"
        exit 1
        ;;
esac

# 发送通知
if [ "$SEVERITY" = "P0" ]; then
    # 发送紧急通知
    curl -X POST "$SLACK_WEBHOOK" -d '{"text":"P0 Incident: '$INCIDENT_TYPE' - Immediate attention required"}'
fi
```

这个运维指南提供了 ChronoRetrace 应用的全面运维操作指导，涵盖了日常监控、故障处理、性能优化和应急响应等各个方面，帮助运维团队高效地管理和维护系统。