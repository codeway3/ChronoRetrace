import React, { useState, useEffect } from 'react';
import { useStockData, useMarketOverview, useWebSocket } from '../hooks/useWebSocket';
import './RealTimeData.css';

/**
 * 实时股票价格组件
 */
export const RealTimeStockPrice = ({ symbol, market = 'us', className = '' }) => {
  const { data, loading, error } = useStockData(symbol, market);
  const [priceChange, setPriceChange] = useState(null);
  const [previousPrice, setPreviousPrice] = useState(null);

  useEffect(() => {
    if (data && data.price !== undefined) {
      if (previousPrice !== null) {
        const change = data.price - previousPrice;
        setPriceChange(change);

        // 3秒后清除价格变化指示
        const timer = setTimeout(() => setPriceChange(null), 3000);
        return () => clearTimeout(timer);
      }
      setPreviousPrice(data.price);
    }
  }, [data, previousPrice]);

  if (loading) {
    return (
      <div className={`real-time-stock-price loading ${className}`}>
        <div className="loading-spinner"></div>
        <span>加载中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`real-time-stock-price error ${className}`}>
        <span>数据加载失败</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className={`real-time-stock-price no-data ${className}`}>
        <span>暂无数据</span>
      </div>
    );
  }

  const changeClass = priceChange > 0 ? 'price-up' : priceChange < 0 ? 'price-down' : '';
  const changePercent = data.previous_close ? ((data.price - data.previous_close) / data.previous_close * 100) : 0;

  return (
    <div className={`real-time-stock-price ${changeClass} ${className}`}>
      <div className="stock-symbol">{symbol}</div>
      <div className="price-info">
        <span className="current-price">${data.price?.toFixed(2)}</span>
        {data.previous_close && (
          <span className={`price-change ${changePercent >= 0 ? 'positive' : 'negative'}`}>
            {changePercent >= 0 ? '+' : ''}{changePercent.toFixed(2)}%
          </span>
        )}
      </div>
      {data.volume && (
        <div className="volume-info">
          <span>成交量: {data.volume.toLocaleString()}</span>
        </div>
      )}
      <div className="last-updated">
        {data.timestamp && new Date(data.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
};

/**
 * 实时市场概览组件
 */
export const RealTimeMarketOverview = ({ market = 'us', className = '' }) => {
  const { data, loading, error } = useMarketOverview(market);

  if (loading) {
    return (
      <div className={`real-time-market-overview loading ${className}`}>
        <div className="loading-spinner"></div>
        <span>加载市场数据...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`real-time-market-overview error ${className}`}>
        <span>市场数据加载失败</span>
      </div>
    );
  }

  if (!data || !data.indices) {
    return (
      <div className={`real-time-market-overview no-data ${className}`}>
        <span>暂无市场数据</span>
      </div>
    );
  }

  return (
    <div className={`real-time-market-overview ${className}`}>
      <h3>市场概览 - {market.toUpperCase()}</h3>
      <div className="indices-grid">
        {data.indices.map((index, i) => (
          <div key={i} className="index-card">
            <div className="index-name">{index.name}</div>
            <div className="index-value">{index.value?.toFixed(2)}</div>
            <div className={`index-change ${index.change >= 0 ? 'positive' : 'negative'}`}>
              {index.change >= 0 ? '+' : ''}{index.change?.toFixed(2)}
              ({index.change_percent >= 0 ? '+' : ''}{index.change_percent?.toFixed(2)}%)
            </div>
          </div>
        ))}
      </div>
      {data.timestamp && (
        <div className="last-updated">
          更新时间: {new Date(data.timestamp).toLocaleString()}
        </div>
      )}
    </div>
  );
};

/**
 * 实时股票列表组件
 */
export const RealTimeStockList = ({ symbols, market = 'us', className = '' }) => {
  const { isConnected } = useWebSocket();

  if (!isConnected) {
    return (
      <div className={`real-time-stock-list disconnected ${className}`}>
        <span>连接已断开，正在重连...</span>
      </div>
    );
  }

  return (
    <div className={`real-time-stock-list ${className}`}>
      <h3>实时股票数据</h3>
      <div className="stocks-grid">
        {symbols.map(symbol => (
          <RealTimeStockPrice
            key={symbol}
            symbol={symbol}
            market={market}
            className="stock-item"
          />
        ))}
      </div>
    </div>
  );
};

/**
 * WebSocket连接状态指示器
 */
export const WebSocketStatus = ({ className = '' }) => {
  const { connectionStatus, error, getStatus } = useWebSocket();
  const [statusDetails, setStatusDetails] = useState(null);

  useEffect(() => {
    const updateStatus = () => {
      setStatusDetails(getStatus());
    };

    updateStatus();
    const interval = setInterval(updateStatus, 1000);
    return () => clearInterval(interval);
  }, [getStatus]);

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'green';
      case 'connecting': return 'orange';
      case 'disconnected': return 'red';
      default: return 'gray';
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return '已连接';
      case 'connecting': return '连接中';
      case 'disconnected': return '已断开';
      default: return '未知';
    }
  };

  return (
    <div className={`websocket-status ${className}`}>
      <div className="status-indicator">
        <div
          className="status-dot"
          style={{ backgroundColor: getStatusColor() }}
        ></div>
        <span className="status-text">{getStatusText()}</span>
      </div>

      {statusDetails && (
        <div className="status-details">
          <div>订阅数: {statusDetails.subscriptions.length}</div>
          {statusDetails.reconnectAttempts > 0 && (
            <div>重连次数: {statusDetails.reconnectAttempts}</div>
          )}
        </div>
      )}

      {error && (
        <div className="status-error">
          错误: {error.message || '连接失败'}
        </div>
      )}
    </div>
  );
};

/**
 * 实时数据仪表板
 */
export const RealTimeDashboard = ({
  watchlist = [],
  market = 'us',
  showMarketOverview = true,
  className = ''
}) => {
  const { isConnected, connect } = useWebSocket();

  const handleReconnect = () => {
    if (!isConnected) {
      connect();
    }
  };

  return (
    <div className={`real-time-dashboard ${className}`}>
      <div className="dashboard-header">
        <h2>实时数据仪表板</h2>
        <div className="dashboard-controls">
          <WebSocketStatus />
          {!isConnected && (
            <button onClick={handleReconnect} className="reconnect-btn">
              重新连接
            </button>
          )}
        </div>
      </div>

      {showMarketOverview && (
        <div className="market-overview-section">
          <RealTimeMarketOverview market={market} />
        </div>
      )}

      {watchlist.length > 0 && (
        <div className="watchlist-section">
          <RealTimeStockList
            symbols={watchlist}
            market={market}
          />
        </div>
      )}

      {watchlist.length === 0 && (
        <div className="empty-watchlist">
          <p>请添加股票到关注列表以查看实时数据</p>
        </div>
      )}
    </div>
  );
};
