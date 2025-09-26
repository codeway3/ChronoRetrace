/**
 * WebSocket 实时数据服务
 * 提供与后端WebSocket连接的管理和数据订阅功能
 */

class WebSocketService {
  constructor() {
    this.ws = null;
    this.url = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_WS_URL) || 'ws://localhost:8000/api/v1/ws/connect';
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 1000; // 1秒
    this.isConnecting = false;
    this.isManualClose = false;

    // 事件监听器
    this.listeners = {
      open: [],
      close: [],
      error: [],
      message: [],
      data: new Map() // topic -> [callbacks]
    };

    // 订阅状态
    this.subscriptions = new Set();
    this.pendingSubscriptions = new Set();

    // 心跳
    this.heartbeatInterval = null;
    this.heartbeatTimeout = null;
    this.heartbeatIntervalMs = 30000; // 30秒
    this.heartbeatTimeoutMs = 5000; // 5秒
  }

  /**
   * 连接WebSocket
   */
  connect(token = null) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return Promise.resolve();
    }

    if (this.isConnecting) {
      console.log('WebSocket connection already in progress');
      return Promise.resolve();
    }

    this.isConnecting = true;
    this.isManualClose = false;

    return new Promise((resolve, reject) => {
      try {
        // 构建连接URL，包含认证token
        let wsUrl = this.url;
        if (token) {
          wsUrl += `?token=${encodeURIComponent(token)}`;
        }

        console.log('Connecting to WebSocket:', wsUrl);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = (event) => {
          console.log('WebSocket connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;

          // 启动心跳
          this.startHeartbeat();

          // 重新订阅之前的主题
          this.resubscribe();

          // 触发open事件
          this.listeners.open.forEach(callback => callback(event));
          resolve();
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.isConnecting = false;

          // 停止心跳
          this.stopHeartbeat();

          // 触发close事件
          this.listeners.close.forEach(callback => callback(event));

          // 自动重连（除非是手动关闭）
          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.isConnecting = false;

          // 触发error事件
          this.listeners.error.forEach(callback => callback(error));
          reject(error);
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.isManualClose = true;
    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }

    // 清空订阅
    this.subscriptions.clear();
    this.pendingSubscriptions.clear();
  }

  /**
   * 处理收到的消息
   */
  handleMessage(event) {
    try {
      const message = JSON.parse(event.data);

      // 触发通用message事件
      this.listeners.message.forEach(callback => callback(message));

      // 处理不同类型的消息
      switch (message.type) {
        case 'data':
          this.handleDataMessage(message);
          break;
        case 'pong':
          this.handlePongMessage(message);
          break;
        case 'subscription_confirmed':
          this.handleSubscriptionConfirmed(message);
          break;
        case 'subscription_error':
          this.handleSubscriptionError(message);
          break;
        case 'error':
          console.error('Server error:', message.data);
          break;
        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error, event.data);
    }
  }

  /**
   * 处理数据消息
   */
  handleDataMessage(message) {
    const { topic, data } = message;

    if (this.listeners.data.has(topic)) {
      this.listeners.data.get(topic).forEach(callback => {
        try {
          callback(data, topic);
        } catch (error) {
          console.error('Error in data callback:', error);
        }
      });
    }
  }

  /**
   * 处理心跳响应
   */
  handlePongMessage(message) {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  /**
   * 处理订阅确认
   */
  handleSubscriptionConfirmed(message) {
    const { topic } = message.data;
    this.subscriptions.add(topic);
    this.pendingSubscriptions.delete(topic);
    console.log('Subscription confirmed:', topic);
  }

  /**
   * 处理订阅错误
   */
  handleSubscriptionError(message) {
    const { topic, error } = message.data;
    this.pendingSubscriptions.delete(topic);
    console.error('Subscription error:', topic, error);
  }

  /**
   * 订阅主题
   */
  subscribe(topic, callback) {
    // 添加回调
    if (!this.listeners.data.has(topic)) {
      this.listeners.data.set(topic, []);
    }
    this.listeners.data.get(topic).push(callback);

    // 如果已连接，立即发送订阅请求，否则加入待订阅列表
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendSubscription(topic);
    } else {
      this.pendingSubscriptions.add(topic);
    }
  }

  /**
   * 取消订阅主题
   */
  unsubscribe(topic, callback = null) {
    if (callback) {
      if (this.listeners.data.has(topic)) {
        const callbacks = this.listeners.data.get(topic);
        const index = callbacks.indexOf(callback);
        if (index !== -1) {
          callbacks.splice(index, 1);
        }
        if (callbacks.length === 0) {
          this.listeners.data.delete(topic);
        }
      }
    } else {
      this.listeners.data.delete(topic);
    }

    // 如果已连接，发送取消订阅请求
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendUnsubscription(topic);
    }
  }

  /**
   * 发送订阅消息
   */
  sendSubscription(topic) {
    const message = {
      type: 'subscribe',
      topic
    };
    this.send(message);
  }

  /**
   * 发送取消订阅消息
   */
  sendUnsubscription(topic) {
    const message = {
      type: 'unsubscribe',
      topic
    };
    this.send(message);
  }

  /**
   * 重新订阅所有主题
   */
  resubscribe() {
    this.pendingSubscriptions.forEach(topic => {
      this.sendSubscription(topic);
      this.pendingSubscriptions.delete(topic);
    });
  }

  /**
   * 发送消息到服务器
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  /**
   * 启动心跳机制
   */
  startHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const pingMessage = { type: 'ping' };
        this.ws.send(JSON.stringify(pingMessage));

        // 设置心跳超时
        if (this.heartbeatTimeout) {
          clearTimeout(this.heartbeatTimeout);
        }
        this.heartbeatTimeout = setTimeout(() => {
          console.warn('Heartbeat timeout - closing connection');
          this.ws.close(4000, 'Heartbeat timeout');
        }, this.heartbeatTimeoutMs);
      }
    }, this.heartbeatIntervalMs);
  }

  /**
   * 停止心跳机制
   */
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  /**
   * 安排重连
   */
  scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectInterval * Math.pow(2, this.reconnectAttempts), 30000);
    console.log(`Scheduling reconnect in ${delay}ms`);
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * 检查连接状态
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * 添加事件监听器
   */
  addEventListener(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  /**
   * 移除事件监听器
   */
  removeEventListener(event, callback) {
    if (this.listeners[event]) {
      const index = this.listeners[event].indexOf(callback);
      if (index !== -1) {
        this.listeners[event].splice(index, 1);
      }
    }
  }

  /**
   * 获取连接状态信息
   */
  getStatus() {
    return {
      isConnected: this.isConnected(),
      reconnectAttempts: this.reconnectAttempts,
      subscriptionsCount: this.subscriptions.size
    };
  }
}

const websocketService = new WebSocketService();

export default websocketService;
