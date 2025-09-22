import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Input, List, Typography, Space, Tag, message } from 'antd';

const { Title, Text } = Typography;

const WebSocketTest = () => {
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const connect = () => {
    try {
      // 连接到WebSocket服务器
      const websocket = new WebSocket('ws://localhost:8000/api/v1/ws/frontend_client');

      websocket.onopen = () => {
        console.log('WebSocket连接已建立');
        setConnected(true);
        setWs(websocket);
        addMessage('系统', '连接已建立', 'success');
      };

      websocket.onmessage = (event) => {
        console.log('收到消息:', event.data);
        try {
          const data = JSON.parse(event.data);
          addMessage('服务器', JSON.stringify(data, null, 2), 'info');
        } catch (e) {
          addMessage('服务器', event.data, 'info');
        }
      };

      websocket.onclose = () => {
        console.log('WebSocket连接已关闭');
        setConnected(false);
        setWs(null);
        addMessage('系统', '连接已关闭', 'warning');
      };

      websocket.onerror = (error) => {
        console.error('WebSocket错误:', error);
        addMessage('系统', '连接错误', 'error');
      };

    } catch (error) {
      console.error('连接失败:', error);
      message.error('连接失败');
    }
  };

  const disconnect = () => {
    if (ws) {
      ws.close();
    }
  };

  const sendMessage = () => {
    if (ws && connected && inputMessage.trim()) {
      try {
        const messageObj = JSON.parse(inputMessage);
        ws.send(JSON.stringify(messageObj));
        addMessage('客户端', inputMessage, 'default');
        setInputMessage('');
      } catch (e) {
        // 如果不是JSON，直接发送
        ws.send(inputMessage);
        addMessage('客户端', inputMessage, 'default');
        setInputMessage('');
      }
    }
  };

  const addMessage = (sender, content, type) => {
    const newMessage = {
      id: Date.now(),
      sender,
      content,
      type,
      timestamp: new Date().toLocaleTimeString()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const sendTestMessages = () => {
    if (!connected) {
      message.warning('请先连接WebSocket');
      return;
    }

    // 发送订阅消息 (正确格式: type.symbol.interval)
    const subscribeMessage = {
      type: 'subscribe',
      topic: 'stock.AAPL.1m'
    };

    ws.send(JSON.stringify(subscribeMessage));
    addMessage('客户端', JSON.stringify(subscribeMessage, null, 2), 'default');
  };

  const clearMessages = () => {
    setMessages([]);
  };

  return (
    <div style={{ padding: '20px' }}>
      <Title level={2}>WebSocket 测试页面</Title>

      <Card title="连接控制" style={{ marginBottom: '20px' }}>
        <Space>
          <Button
            type="primary"
            onClick={connect}
            disabled={connected}
          >
            连接
          </Button>
          <Button
            onClick={disconnect}
            disabled={!connected}
          >
            断开连接
          </Button>
          <Tag color={connected ? 'green' : 'red'}>
            {connected ? '已连接' : '未连接'}
          </Tag>
        </Space>
      </Card>

      <Card title="发送消息" style={{ marginBottom: '20px' }}>
        <Space.Compact style={{ width: '100%', marginBottom: '10px' }}>
          <Input
            placeholder="输入JSON消息，例如: {&quot;action&quot;: &quot;subscribe&quot;, &quot;topic&quot;: &quot;stock_data&quot;}"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onPressEnter={sendMessage}
            disabled={!connected}
          />
          <Button
            type="primary"
            onClick={sendMessage}
            disabled={!connected || !inputMessage.trim()}
          >
            发送
          </Button>
        </Space.Compact>
        <Space>
          <Button onClick={sendTestMessages} disabled={!connected}>
            发送测试消息
          </Button>
          <Button onClick={clearMessages}>
            清空消息
          </Button>
        </Space>
      </Card>

      <Card title="消息日志">
        <div style={{ height: '400px', overflowY: 'auto' }}>
          <List
            dataSource={messages}
            renderItem={(item) => (
              <List.Item>
                <div style={{ width: '100%' }}>
                  <div style={{ marginBottom: '5px' }}>
                    <Tag color={
                      item.type === 'success' ? 'green' :
                      item.type === 'error' ? 'red' :
                      item.type === 'warning' ? 'orange' :
                      item.type === 'info' ? 'blue' : 'default'
                    }>
                      {item.sender}
                    </Tag>
                    <Text type="secondary">{item.timestamp}</Text>
                  </div>
                  <pre style={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    margin: 0,
                    fontSize: '12px'
                  }}>
                    {item.content}
                  </pre>
                </div>
              </List.Item>
            )}
          />
          <div ref={messagesEndRef} />
        </div>
      </Card>
    </div>
  );
};

export default WebSocketTest;
