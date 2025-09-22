# WebSocket实时数据流处理与支持 - 详细设计方案

## 1. 项目现状分析

### 1.1 现有架构优势
- **后端**: 基于FastAPI的现代化架构，支持异步处理
- **数据层**: 完善的数据获取器架构，支持多种数据源（A股、美股、期货、期权等）
- **缓存**: Redis缓存系统，提供高效的数据访问
- **基础设施**: 已配置Nginx WebSocket代理支持

### 1.2 当前限制
- **数据获取**: 基于HTTP轮询，无法实现真正的实时推送
- **用户体验**: 数据更新延迟，需要手动刷新
- **资源消耗**: 频繁的HTTP请求增加服务器负载

## 2. 整体架构设计

### 2.1 系统架构图
```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   前端客户端     │ ←──────────────→ │   WebSocket     │
│                │                 │   连接管理器     │
└─────────────────┘                 └─────────────────┘
                                           │
                                           ▼
┌─────────────────┐    消息队列     ┌─────────────────┐
│   实时数据      │ ←──────────────→ │   数据处理      │
│   推送服务      │                 │   服务          │
└─────────────────┘                 └─────────────────┘
         │                                 │
         ▼                                 ▼
┌─────────────────┐                ┌─────────────────┐
│   数据源适配器   │                │   缓存层        │
│   (A股/美股等)  │                │   (Redis)       │
└─────────────────┘                └─────────────────┘
```

### 2.2 核心组件
1. **WebSocket连接管理器**: 管理客户端连接生命周期
2. **实时数据推送服务**: 处理数据订阅和推送逻辑
3. **数据源适配器**: 集成现有数据获取器，提供实时数据流
4. **消息路由器**: 根据订阅规则分发数据

## 3. 后端实现方案

### 3.1 WebSocket连接管理器
```python
# app/websocket/connection_manager.py
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str)
    async def disconnect(self, client_id: str)
    async def subscribe(self, client_id: str, topic: str)
    async def unsubscribe(self, client_id: str, topic: str)
    async def broadcast_to_topic(self, topic: str, message: dict)
```

### 3.2 实时数据处理服务
```python
# app/websocket/data_stream_service.py
class DataStreamService:
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.data_fetchers = {}
    
    async def start_real_time_feed(self, symbol: str, interval: str)
    async def stop_real_time_feed(self, symbol: str)
    async def process_market_data(self, data: dict)
```

### 3.3 WebSocket路由设计
```python
# app/api/websocket.py
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    # 连接管理和消息处理逻辑
```

## 4. 前端实现方案

### 4.1 WebSocket客户端封装
```javascript
// src/services/WebSocketService.js
class WebSocketService {
    constructor() {
        this.ws = null;
        this.subscriptions = new Map();
        this.reconnectAttempts = 0;
    }
    
    connect(clientId) { /* 连接逻辑 */ }
    subscribe(topic, callback) { /* 订阅逻辑 */ }
    unsubscribe(topic) { /* 取消订阅 */ }
    send(message) { /* 发送消息 */ }
}
```

### 4.2 React状态管理
```javascript
// src/contexts/WebSocketContext.js
const WebSocketContext = createContext();

export const WebSocketProvider = ({ children }) => {
    const [realTimeData, setRealTimeData] = useState({});
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    
    // WebSocket服务集成
};
```

### 4.3 实时图表组件更新
```javascript
// src/components/RealTimeChart.js
const RealTimeChart = ({ symbol }) => {
    const { subscribeToSymbol, unsubscribeFromSymbol } = useWebSocket();
    
    useEffect(() => {
        subscribeToSymbol(symbol, (data) => {
            // 更新图表数据
        });
        
        return () => unsubscribeFromSymbol(symbol);
    }, [symbol]);
};
```

## 5. 实时数据源集成

### 5.1 数据源适配器设计
```python
# app/data/adapters/realtime_adapter.py
class RealTimeDataAdapter:
    def __init__(self, fetcher_type: str):
        self.fetcher = self._get_fetcher(fetcher_type)
    
    async def start_stream(self, symbols: List[str])
    async def stop_stream(self, symbols: List[str])
    async def get_real_time_data(self, symbol: str)
```

### 5.2 A股实时数据集成
- 集成AKShare实时行情接口
- 支持分钟级数据推送
- 处理交易时间窗口

### 5.3 美股实时数据集成
- 集成Yahoo Finance实时数据
- 支持盘前盘后交易数据
- 处理时区转换

## 6. 消息协议设计

### 6.1 消息格式
```json
{
    "type": "subscribe|unsubscribe|data|error|heartbeat",
    "topic": "stock.AAPL.1m",
    "data": {
        "symbol": "AAPL",
        "price": 150.25,
        "volume": 1000,
        "timestamp": "2024-01-15T10:30:00Z"
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### 6.2 订阅主题规则
- `stock.{symbol}.{interval}`: 股票实时数据
- `crypto.{symbol}.{interval}`: 加密货币数据
- `futures.{symbol}.{interval}`: 期货数据
- `market.{market}.summary`: 市场概览

## 7. 性能优化方案

### 7.1 连接管理优化
- 连接池管理，限制最大连接数
- 心跳检测机制，及时清理无效连接
- 连接复用，减少资源消耗

### 7.2 数据传输优化
- 数据压缩（gzip）
- 增量数据传输
- 批量数据推送

### 7.3 缓存策略
- Redis缓存热点数据
- 本地缓存减少重复计算
- 缓存预热机制

## 8. 安全性设计

### 8.1 认证授权
- JWT Token验证
- 基于角色的订阅权限控制
- 连接频率限制

### 8.2 数据安全
- 敏感数据加密传输
- 订阅权限验证
- 防止数据泄露

## 9. 监控与运维

### 9.1 关键指标
- WebSocket连接数
- 消息推送延迟
- 数据源可用性
- 错误率统计

### 9.2 告警机制
- 连接异常告警
- 数据延迟告警
- 系统资源告警

## 10. 实施计划

### 阶段一：基础架构搭建（1-2天）
1. 实现WebSocket连接管理器
2. 创建基础消息协议
3. 搭建前端WebSocket服务

### 阶段二：数据流集成（2-3天）
1. 集成现有数据获取器
2. 实现实时数据推送服务
3. 创建数据源适配器

### 阶段三：前端集成（1-2天）
1. 实现React WebSocket集成
2. 更新图表组件支持实时数据
3. 添加连接状态管理

### 阶段四：优化与测试（1-2天）
1. 性能优化和压力测试
2. 安全性验证
3. 监控指标配置

## 11. 预期效果

### 11.1 技术指标
- 数据推送延迟 < 100ms
- 支持1000+并发连接
- 99.9%的服务可用性

### 11.2 用户体验提升
- 实时数据更新，无需手动刷新
- 流畅的图表动画效果
- 更好的交互响应性

## 12. 风险评估与应对

### 12.1 技术风险
- **数据源限制**: 部分数据源可能不支持实时推送
- **应对**: 采用混合模式，结合轮询和推送

### 12.2 性能风险
- **高并发压力**: 大量连接可能影响系统性能
- **应对**: 实施连接限制和负载均衡

### 12.3 稳定性风险
- **网络中断**: WebSocket连接可能因网络问题中断
- **应对**: 实现自动重连和断线恢复机制