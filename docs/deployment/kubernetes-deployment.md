# Kubernetes 部署指南

本文档详细介绍如何在 Kubernetes 集群中部署 ChronoRetrace 应用。

## 目录

- [集群准备](#集群准备)
- [命名空间管理](#命名空间管理)
- [配置管理](#配置管理)
- [存储配置](#存储配置)
- [网络配置](#网络配置)
- [应用部署](#应用部署)
- [服务暴露](#服务暴露)
- [自动扩缩容](#自动扩缩容)
- [监控和日志](#监控和日志)
- [安全配置](#安全配置)
- [故障排除](#故障排除)

## 集群准备

### 集群要求
- Kubernetes 版本: 1.20+
- 节点数量: 3+ (生产环境)
- CPU: 8+ 核心 (总计)
- 内存: 16GB+ (总计)
- 存储: 支持动态卷供应

### 必需组件
```bash
# 安装 kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 安装 Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 验证集群连接
kubectl cluster-info
kubectl get nodes
```

### 集群插件
```bash
# 安装 Ingress Controller (NGINX)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.5.1/deploy/static/provider/cloud/deploy.yaml

# 安装 Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 安装 Cert-Manager (可选)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.10.1/cert-manager.yaml
```

## 命名空间管理

### 创建命名空间
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: chronoretrace
  labels:
    name: chronoretrace
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: chronoretrace-staging
  labels:
    name: chronoretrace-staging
    environment: staging
```

```bash
# 应用命名空间
kubectl apply -f namespace.yaml

# 设置默认命名空间
kubectl config set-context --current --namespace=chronoretrace
```

### 资源配额
```yaml
# resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: chronoretrace-quota
  namespace: chronoretrace
spec:
  hard:
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
    persistentvolumeclaims: "10"
    services: "10"
    secrets: "20"
    configmaps: "20"
```

## 配置管理

### ConfigMap 配置
```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: chronoretrace-config
  namespace: chronoretrace
data:
  app.conf: |
    [database]
    host = chronoretrace-postgres
    port = 5432
    name = chronoretrace

    [redis]
    host = chronoretrace-redis
    port = 6379
    db = 0

    [logging]
    level = info
    format = json

  nginx.conf: |
    upstream backend {
        server chronoretrace-backend:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location / {
            proxy_pass http://chronoretrace-frontend:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
```

### Secret 管理
```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: chronoretrace-secrets
  namespace: chronoretrace
type: Opaque
data:
  database-url: cG9zdGdyZXNxbDovL2Nocm9ub3JldHJhY2U6cGFzc3dvcmRAY2hyb25vcmV0cmFjZS1wb3N0Z3Jlczo1NDMyL2Nocm9ub3JldHJhY2U=
  jwt-secret: eW91ci1qd3Qtc2VjcmV0LWtleQ==
  postgres-password: cGFzc3dvcmQ=
---
apiVersion: v1
kind: Secret
metadata:
  name: chronoretrace-tls
  namespace: chronoretrace
type: kubernetes.io/tls
data:
  tls.crt: LS0tLS1CRUdJTi...
  tls.key: LS0tLS1CRUdJTi...
```

```bash
# 创建 Secret
kubectl create secret generic chronoretrace-secrets \
  --from-literal=database-url="postgresql://chronoretrace:password@chronoretrace-postgres:5432/chronoretrace" \ # pragma: allowlist secret
  --from-literal=jwt-secret="your-jwt-secret-key" \ # pragma: allowlist secret
  --from-literal=postgres-password="password" \ # pragma: allowlist secret
  -n chronoretrace

# 创建 TLS Secret
kubectl create secret tls chronoretrace-tls \
  --cert=tls.crt \
  --key=tls.key \
  -n chronoretrace
```

## 存储配置

### StorageClass
```yaml
# storage-class.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: chronoretrace-ssd
provisioner: kubernetes.io/aws-ebs  # 根据云提供商调整
parameters:
  type: gp3
  fsType: ext4
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

### PersistentVolumeClaim
```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: chronoretrace
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: chronoretrace-ssd
  resources:
    requests:
      storage: 20Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: chronoretrace
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: chronoretrace-ssd
  resources:
    requests:
      storage: 5Gi
```

## 网络配置

### NetworkPolicy
```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chronoretrace-network-policy
  namespace: chronoretrace
spec:
  podSelector:
    matchLabels:
      app: chronoretrace
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    - podSelector:
        matchLabels:
          app: chronoretrace
    ports:
    - protocol: TCP
      port: 8000
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: chronoretrace-postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: chronoretrace-redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []  # 允许所有出站流量
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

## 应用部署

### PostgreSQL 部署
```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chronoretrace-postgres
  namespace: chronoretrace
  labels:
    app: chronoretrace-postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: chronoretrace-postgres
  template:
    metadata:
      labels:
        app: chronoretrace-postgres
    spec:
      containers:
      - name: postgres
        image: postgres:13-alpine
        env:
        - name: POSTGRES_DB
          value: chronoretrace
        - name: POSTGRES_USER
          value: chronoretrace
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: chronoretrace-secrets
              key: postgres-password
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - chronoretrace
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - chronoretrace
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: chronoretrace-postgres
  namespace: chronoretrace
spec:
  selector:
    app: chronoretrace-postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

### Redis 部署
```yaml
# redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chronoretrace-redis
  namespace: chronoretrace
  labels:
    app: chronoretrace-redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: chronoretrace-redis
  template:
    metadata:
      labels:
        app: chronoretrace-redis
    spec:
      containers:
      - name: redis
        image: redis:6-alpine
        command: ["redis-server", "--appendonly", "yes"]
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: chronoretrace-redis
  namespace: chronoretrace
spec:
  selector:
    app: chronoretrace-redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
```

### 后端应用部署
```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chronoretrace-backend
  namespace: chronoretrace
  labels:
    app: chronoretrace-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chronoretrace-backend
  template:
    metadata:
      labels:
        app: chronoretrace-backend
    spec:
      initContainers:
      - name: wait-for-postgres
        image: postgres:13-alpine
        command: ['sh', '-c', 'until pg_isready -h chronoretrace-postgres -p 5432; do echo waiting for postgres; sleep 2; done;']
      - name: migrate-database
        image: chronoretrace-backend:latest
        command: ['python', 'manage.py', 'migrate']
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: chronoretrace-secrets
              key: database-url
      containers:
      - name: backend
        image: chronoretrace-backend:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: chronoretrace-secrets
              key: database-url
        - name: REDIS_URL
          value: "redis://chronoretrace-redis:6379/0"
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: chronoretrace-secrets
              key: jwt-secret
        - name: ENVIRONMENT
          value: "production"
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
      volumes:
      - name: config
        configMap:
          name: chronoretrace-config
---
apiVersion: v1
kind: Service
metadata:
  name: chronoretrace-backend
  namespace: chronoretrace
spec:
  selector:
    app: chronoretrace-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

### 前端应用部署
```yaml
# frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chronoretrace-frontend
  namespace: chronoretrace
  labels:
    app: chronoretrace-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: chronoretrace-frontend
  template:
    metadata:
      labels:
        app: chronoretrace-frontend
    spec:
      containers:
      - name: frontend
        image: chronoretrace-frontend:latest
        env:
        - name: VITE_API_BASE_URL
        value: "https://api.chronoretrace.com"
        ports:
        - containerPort: 3000
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: chronoretrace-frontend
  namespace: chronoretrace
spec:
  selector:
    app: chronoretrace-frontend
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP
```

## 服务暴露

### Ingress 配置
```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: chronoretrace-ingress
  namespace: chronoretrace
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$1
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - chronoretrace.com
    - api.chronoretrace.com
    secretName: chronoretrace-tls
  rules:
  - host: chronoretrace.com
    http:
      paths:
      - path: /(.*)
        pathType: Prefix
        backend:
          service:
            name: chronoretrace-frontend
            port:
              number: 3000
  - host: api.chronoretrace.com
    http:
      paths:
      - path: /(.*)
        pathType: Prefix
        backend:
          service:
            name: chronoretrace-backend
            port:
              number: 8000
```

### LoadBalancer 服务
```yaml
# loadbalancer.yaml
apiVersion: v1
kind: Service
metadata:
  name: chronoretrace-loadbalancer
  namespace: chronoretrace
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
spec:
  type: LoadBalancer
  selector:
    app: chronoretrace-frontend
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
  - port: 443
    targetPort: 3000
    protocol: TCP
```

## 自动扩缩容

### Horizontal Pod Autoscaler
```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: chronoretrace-backend-hpa
  namespace: chronoretrace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: chronoretrace-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

### Vertical Pod Autoscaler
```yaml
# vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: chronoretrace-backend-vpa
  namespace: chronoretrace
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
        cpu: 1
        memory: 2Gi
      minAllowed:
        cpu: 100m
        memory: 128Mi
```

## 监控和日志

### ServiceMonitor (Prometheus)
```yaml
# service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: chronoretrace-backend
  namespace: chronoretrace
  labels:
    app: chronoretrace-backend
spec:
  selector:
    matchLabels:
      app: chronoretrace-backend
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### 日志收集 (Fluentd)
```yaml
# fluentd-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: chronoretrace
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/chronoretrace-*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      format json
      time_format %Y-%m-%dT%H:%M:%S.%NZ
    </source>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch.logging.svc.cluster.local
      port 9200
      index_name chronoretrace
    </match>
```

## 安全配置

### Pod Security Policy
```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: chronoretrace-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### RBAC 配置
```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: chronoretrace-sa
  namespace: chronoretrace
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: chronoretrace-role
  namespace: chronoretrace
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: chronoretrace-rolebinding
  namespace: chronoretrace
subjects:
- kind: ServiceAccount
  name: chronoretrace-sa
  namespace: chronoretrace
roleRef:
  kind: Role
  name: chronoretrace-role
  apiGroup: rbac.authorization.k8s.io
```

## 故障排除

### 常用调试命令
```bash
# 查看 Pod 状态
kubectl get pods -n chronoretrace

# 查看 Pod 详细信息
kubectl describe pod <pod-name> -n chronoretrace

# 查看 Pod 日志
kubectl logs -f <pod-name> -n chronoretrace

# 进入 Pod 调试
kubectl exec -it <pod-name> -n chronoretrace -- /bin/bash

# 查看服务状态
kubectl get svc -n chronoretrace

# 查看 Ingress 状态
kubectl get ingress -n chronoretrace

# 查看事件
kubectl get events -n chronoretrace --sort-by=.metadata.creationTimestamp

# 查看资源使用
kubectl top pods -n chronoretrace
kubectl top nodes
```

### 常见问题解决

#### 1. Pod 无法启动
```bash
# 检查镜像拉取
kubectl describe pod <pod-name> -n chronoretrace | grep -A 10 Events

# 检查资源限制
kubectl describe node <node-name>

# 检查存储
kubectl get pvc -n chronoretrace
```

#### 2. 服务无法访问
```bash
# 检查服务端点
kubectl get endpoints -n chronoretrace

# 测试服务连通性
kubectl run test-pod --image=busybox --rm -it -- wget -qO- http://chronoretrace-backend:8000/health

# 检查网络策略
kubectl get networkpolicy -n chronoretrace
```

#### 3. 性能问题
```bash
# 检查资源使用
kubectl top pods -n chronoretrace

# 检查 HPA 状态
kubectl get hpa -n chronoretrace

# 查看指标
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/chronoretrace/pods
```

### 备份和恢复
```bash
# 备份配置
kubectl get all,configmap,secret,pvc -n chronoretrace -o yaml > chronoretrace-backup.yaml

# 备份数据库
kubectl exec -it chronoretrace-postgres-xxx -n chronoretrace -- pg_dump -U chronoretrace chronoretrace > db-backup.sql

# 恢复配置
kubectl apply -f chronoretrace-backup.yaml

# 恢复数据库
kubectl exec -i chronoretrace-postgres-xxx -n chronoretrace -- psql -U chronoretrace chronoretrace < db-backup.sql
```

## 部署脚本

### 一键部署脚本
```bash
#!/bin/bash
# deploy.sh

set -e

NAMESPACE="chronoretrace"
ENVIRONMENT="production"

echo "Deploying ChronoRetrace to Kubernetes..."

# 创建命名空间
kubectl apply -f namespace.yaml

# 应用配置
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# 应用存储
kubectl apply -f storage-class.yaml
kubectl apply -f pvc.yaml

# 部署数据库
kubectl apply -f postgres-deployment.yaml
kubectl apply -f redis-deployment.yaml

# 等待数据库就绪
echo "Waiting for database to be ready..."
kubectl wait --for=condition=ready pod -l app=chronoretrace-postgres -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=chronoretrace-redis -n $NAMESPACE --timeout=300s

# 部署应用
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml

# 等待应用就绪
echo "Waiting for applications to be ready..."
kubectl wait --for=condition=ready pod -l app=chronoretrace-backend -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app=chronoretrace-frontend -n $NAMESPACE --timeout=300s

# 配置网络
kubectl apply -f ingress.yaml
kubectl apply -f network-policy.yaml

# 配置自动扩缩容
kubectl apply -f hpa.yaml

# 配置监控
kubectl apply -f service-monitor.yaml

echo "Deployment completed successfully!"
echo "Access the application at: https://chronoretrace.com"
```

这个 Kubernetes 部署指南提供了从集群准备到生产环境部署的完整流程，包括安全配置、监控、自动扩缩容和故障排除等最佳实践。
