# 🚀 ChronoRetrace 快速部署

一个简单易用的部署指南，让任何人都能快速部署 ChronoRetrace。

## ⚡ 一键部署

### 第一步：下载项目
```bash
git clone https://github.com/codeway3/ChronoRetrace.git
cd ChronoRetrace
```

### 第二步：运行部署脚本
```bash
./quick-deploy.sh
```

### 第三步：访问应用
- 🌐 前端: http://localhost:3000
- 🔧 后端 API: http://localhost:8000
- 👤 管理后台: http://localhost:8000/admin

**默认账号**: admin / admin123

## 📋 支持的系统

- ✅ macOS 10.15+
- ✅ Ubuntu 18.04+
- ✅ 自动检测 Docker 环境

## 🛠️ 常用命令

```bash
# 停止服务
./quick-deploy.sh stop

# 查看日志
tail -f logs/backend.log
tail -f logs/frontend.log

# Docker 方式查看状态
docker-compose ps
docker-compose logs -f
```

## 📚 详细文档

- [完整部署指南](docs/deployment.md) - 包含故障排除和高级配置
- [专业部署方案](docs/deployment/) - Kubernetes、负载均衡等企业级部署

## 🆘 遇到问题？

1. 查看 [故障排除指南](docs/deployment.md#故障排除)
2. 检查 [GitHub Issues](https://github.com/codeway3/ChronoRetrace/issues)
3. 提交新的 Issue

---

**提示**: 这是最简化的部署方案。生产环境请参考详细文档进行安全配置。
