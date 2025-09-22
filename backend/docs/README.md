# Backend 文档

## WebSocket 实时数据流

### 文档
- [WebSocket 使用说明](./websocket_usage_guide.md) - 完整的API文档和使用指南
- [WebSocket 测试案例](./websocket_test_cases.md) - 测试场景和验证结果

### 测试
WebSocket相关的测试文件位于 `../tests/` 目录：
- `test_websocket_basic.py` - 基础连接和功能测试
- `test_websocket_subscription.py` - 订阅功能专项测试

### 快速开始

1. **启动后端服务**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **运行测试**
   ```bash
   cd backend/tests
   python test_websocket_basic.py
   python test_websocket_subscription.py
   ```

3. **连接WebSocket**
   ```
   ws://localhost:8000/api/v1/ws/{client_id}
   ```

### 其他文档
- [缓存架构设计](./cache_architecture_design.md)
- [部署说明](./deployment.md)
- [用户认证开发计划](./user_auth_development_plan.md)