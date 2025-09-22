import { useState, useEffect, useCallback, useRef, useContext } from 'react';
import websocketService from '../services/websocketService';
import AuthContext from '../contexts/AuthContext';

/**
 * WebSocket Hook
 * 提供在React组件中使用WebSocket的便捷接口
 */
export const useWebSocket = () => {
  const { token } = useContext(AuthContext);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);

  const statusRef = useRef(connectionStatus);
  statusRef.current = connectionStatus;

  // 连接WebSocket
  const connect = useCallback(async () => {
    try {
      setError(null);
      setConnectionStatus('connecting');
      await websocketService.connect(token);
      setConnectionStatus('connected');
    } catch (err) {
      setError(err);
      setConnectionStatus('disconnected');
    }
  }, [token]);

  // 断开连接
  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setConnectionStatus('disconnected');
  }, []);

  // 发送消息
  const sendMessage = useCallback((message) => {
    websocketService.send(message);
  }, []);

  // 获取连接状态详情
  const getStatus = useCallback(() => {
    return websocketService.getStatus();
  }, []);

  useEffect(() => {
    // 监听连接事件
    const handleOpen = () => {
      setConnectionStatus('connected');
      setError(null);
    };

    const handleClose = () => {
      setConnectionStatus('disconnected');
    };

    const handleError = (error) => {
      setError(error);
      setConnectionStatus('disconnected');
    };

    const handleMessage = (message) => {
      setLastMessage(message);
    };

    // 添加事件监听器
    websocketService.addEventListener('open', handleOpen);
    websocketService.addEventListener('close', handleClose);
    websocketService.addEventListener('error', handleError);
    websocketService.addEventListener('message', handleMessage);

    // 如果有token且未连接，自动连接
    if (token && !websocketService.isConnected()) {
      connect();
    }

    // 清理函数
    return () => {
      websocketService.removeEventListener('open', handleOpen);
      websocketService.removeEventListener('close', handleClose);
      websocketService.removeEventListener('error', handleError);
      websocketService.removeEventListener('message', handleMessage);
    };
  }, [token, connect]);

  return {
    connectionStatus,
    lastMessage,
    error,
    connect,
    disconnect,
    sendMessage,
    getStatus,
    isConnected: connectionStatus === 'connected'
  };
};

/**
 * 数据订阅Hook
 * 用于订阅特定主题的实时数据
 */
export const useWebSocketData = (topic, options = {}) => {
  const { enabled = true, onData, onError } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const unsubscribeRef = useRef(null);

  const subscribe = useCallback(() => {
    if (!topic || !enabled) return;

    setLoading(true);
    setError(null);

    const handleData = (newData, receivedTopic) => {
      if (receivedTopic === topic) {
        setData(newData);
        setLoading(false);
        if (onData) {
          onData(newData, receivedTopic);
        }
      }
    };

    const handleError = (err) => {
      setError(err);
      setLoading(false);
      if (onError) {
        onError(err);
      }
    };

    try {
      unsubscribeRef.current = websocketService.subscribe(topic, handleData);
    } catch (err) {
      handleError(err);
    }
  }, [topic, enabled, onData, onError]);

  const unsubscribe = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (enabled && websocketService.isConnected()) {
      subscribe();
    }

    return unsubscribe;
  }, [subscribe, unsubscribe, enabled]);

  // 监听连接状态变化，重新订阅
  useEffect(() => {
    const handleOpen = () => {
      if (enabled) {
        subscribe();
      }
    };

    const handleClose = () => {
      setLoading(false);
    };

    websocketService.addEventListener('open', handleOpen);
    websocketService.addEventListener('close', handleClose);

    return () => {
      websocketService.removeEventListener('open', handleOpen);
      websocketService.removeEventListener('close', handleClose);
    };
  }, [subscribe, enabled]);

  return {
    data,
    loading,
    error,
    subscribe,
    unsubscribe
  };
};

/**
 * 股票数据Hook
 * 专门用于订阅股票实时数据
 */
export const useStockData = (symbol, market = 'us', options = {}) => {
  const topic = symbol ? `stock.${market}.${symbol}` : null;
  return useWebSocketData(topic, options);
};

/**
 * 市场概览Hook
 * 用于订阅市场概览数据
 */
export const useMarketOverview = (market = 'us', options = {}) => {
  const topic = `market.${market}.overview`;
  return useWebSocketData(topic, options);
};

/**
 * 加密货币数据Hook
 * 用于订阅加密货币实时数据
 */
export const useCryptoData = (symbol, options = {}) => {
  const topic = symbol ? `crypto.${symbol}` : null;
  return useWebSocketData(topic, options);
};

/**
 * 期货数据Hook
 * 用于订阅期货实时数据
 */
export const useFuturesData = (symbol, options = {}) => {
  const topic = symbol ? `futures.${symbol}` : null;
  return useWebSocketData(topic, options);
};
