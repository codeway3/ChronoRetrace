# WebSocket 实时数据流使用说明

## 概述

ChronoRetrace 提供了完整的 WebSocket 实时数据流功能，支持股票、加密货币、期货等多种金融数据的实时订阅和推送。

## 连接地址

```
ws://localhost:8000/api/v1/ws/{client_id}
```

其中 `{client_id}` 是客户端的唯一标识符，可以是任意字符串。

## 消息格式

所有消息都使用 JSON 格式，包含 `type` 字段标识消息类型。

### 1. 连接确认

客户端连接成功后，服务器会发送连接确认消息：

```json
{
    "type": "connection_ack",
    "client_id": "your_client_id",
    "timestamp": "2025-09-22T05:16:02.800339"
}
```

### 2. 订阅数据

#### 订阅请求

```json
{
    "type": "subscribe",
    "topic": "stock.AAPL.1m"
}
```

#### 主题格式

主题格式为：`{type}.{symbol}.{interval}`

**支持的数据类型：**
- `stock` - 股票
- `crypto` - 加密货币
- `futures` - 期货
- `options` - 期权
- `commodity` - 商品
- `market` - 市场概览

**时间间隔：**
- `1m`, `5m`, `15m`, `30m` - 分钟级别
- `1h`, `4h` - 小时级别
- `1d` - 日级别
- `1w` - 周级别
- `1M` - 月级别

**示例主题：**
- `stock.AAPL.1m` - 苹果股票1分钟数据
- `crypto.BTC.5m` - 比特币5分钟数据
- `futures.CL.1h` - 原油期货1小时数据
- `market.US.summary` - 美国市场概览

#### 订阅确认

```json
{
    "type": "subscribe_ack",
    "topic": "stock.AAPL.1m",
    "timestamp": "2025-09-22T05:16:02.806786"
}
```

### 3. 取消订阅

#### 取消订阅请求

```json
{
    "type": "unsubscribe",
    "topic": "stock.AAPL.1m"
}
```

#### 取消订阅确认

```json
{
    "type": "unsubscribe_ack",
    "topic": "stock.AAPL.1m",
    "timestamp": "2025-09-22T05:16:27.841205"
}
```

### 4. 心跳机制

#### Ping 请求

```json
{
    "type": "ping"
}
```

#### Pong 响应

```json
{
    "type": "pong",
    "timestamp": "2025-09-22T05:16:27.858837"
}
```

### 5. 错误消息

```json
{
    "type": "error",
    "error_code": "invalid_topic",
    "error_message": "无效的主题格式: stock_data",
    "timestamp": "2025-09-22T05:14:39.139106"
}
```

**常见错误代码：**
- `invalid_topic` - 无效的主题格式
- `invalid_message` - 无效的消息格式
- `subscription_failed` - 订阅失败

## 使用示例

### Python 客户端示例

```python
import asyncio
import json
import websockets

async def websocket_client():
    client_id = "my_client"
    uri = f"ws://localhost:8000/api/v1/ws/{client_id}"

    async with websockets.connect(uri) as websocket:
        # 等待连接确认
        response = await websocket.recv()
        print(f"连接确认: {response}")

        # 订阅苹果股票1分钟数据
        subscribe_message = {
            "type": "subscribe",
            "topic": "stock.AAPL.1m"
        }
        await websocket.send(json.dumps(subscribe_message))

        # 监听消息
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"收到消息: {data}")
            except websockets.exceptions.ConnectionClosed:
                break

# 运行客户端
asyncio.run(websocket_client())
```

### JavaScript 客户端示例

```javascript
const clientId = 'my_client';
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/${clientId}`);

ws.onopen = function() {
    console.log('WebSocket 连接已建立');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);

    // 如果是连接确认，发送订阅请求
    if (data.type === 'connection_ack') {
        const subscribeMessage = {
            type: 'subscribe',
            topic: 'stock.AAPL.1m'
        };
        ws.send(JSON.stringify(subscribeMessage));
    }
};

ws.onclose = function() {
    console.log('WebSocket 连接已关闭');
};

ws.onerror = function(error) {
    console.error('WebSocket 错误:', error);
};
```

## 前端测试页面

访问 `http://localhost:3000/websocket-test` 可以使用内置的 WebSocket 测试页面，该页面提供了：

- 连接/断开 WebSocket
- 发送测试订阅消息
- 实时显示收发消息
- 连接状态监控

## 最佳实践

1. **连接管理**
   - 使用唯一的 client_id 避免冲突
   - 实现重连机制处理网络中断
   - 正确处理连接关闭事件

2. **订阅管理**
   - 避免重复订阅相同主题
   - 及时取消不需要的订阅
   - 验证主题格式的正确性

3. **错误处理**
   - 监听错误消息并适当处理
   - 实现消息解析异常处理
   - 记录连接和订阅状态

4. **性能优化**
   - 合理控制订阅数量
   - 使用适当的时间间隔
   - 实现消息缓冲和批处理

## 故障排除

### 常见问题

1. **连接失败**
   - 检查服务器是否运行在 8000 端口
   - 确认 client_id 格式正确
   - 检查网络连接

2. **订阅失败**
   - 验证主题格式是否正确
   - 检查数据类型和时间间隔是否支持
   - 确认消息 JSON 格式正确

3. **消息接收异常**
   - 检查消息解析逻辑
   - 验证 WebSocket 连接状态
   - 查看服务器日志获取详细错误信息

### 调试工具

- 使用浏览器开发者工具的网络面板监控 WebSocket 连接
- 查看服务器日志文件获取详细错误信息
- 使用内置测试页面验证功能

## 技术支持

如有问题，请查看：
- 服务器日志：`backend/logs/`
- 项目文档：`README.md`
- 问题反馈：GitHub Issues
