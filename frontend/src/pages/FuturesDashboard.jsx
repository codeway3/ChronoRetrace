import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Select, message, Spin, Row, Col, Card, Typography, Radio } from 'antd';
import StockChart from '../components/StockChart';
import { getFuturesData, getFuturesList } from '../api/stockApi';

const { Option } = Select;
const { Title, Text } = Typography;

const FuturesDashboard = () => {
  const [allFutures, setAllFutures] = useState([]);
  const [selectedFuture, setSelectedFuture] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [displayedFutureCode, setDisplayedFutureCode] = useState(null);
  const [displayedFutureName, setDisplayedFutureName] = useState(null);
  const [selectedInterval, setSelectedInterval] = useState('daily');
  const [error, setError] = useState(null);
  const debounceTimeout = useRef(null);

  const title = '期货市场';
  const placeholder = '搜索或选择期货 (例如: ES=F)';

  const fetchData = useCallback((symbol, interval) => {
    if (!symbol) return;
    if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
    setLoading(true);
    setChartData([]);
    setError(null);

    debounceTimeout.current = setTimeout(() => {
      getFuturesData(symbol, interval)
        .then(response => {
          setChartData(response.data);
        })
        .catch(error => {
          const errorMsg = error.response?.data?.detail || `加载 ${symbol} 数据失败。`;
          setError(errorMsg);
          message.error(errorMsg);
          setChartData([]);
        })
        .finally(() => setLoading(false));
    }, 500);
  }, []);

  useEffect(() => {
    if (selectedFuture) {
      fetchData(selectedFuture, selectedInterval);
    }
  }, [selectedFuture, selectedInterval, fetchData]);

  useEffect(() => {
    setLoading(true);
    getFuturesList()
      .then(response => {
        const futures = Object.entries(response.data).map(([symbol, name]) => ({
          ts_code: symbol,
          name: `${name} (${symbol})`,
          raw_name: name,
        }));
        setAllFutures(futures);
        if (futures.length > 0) {
          const initialFuture = futures[0];
          setSelectedFuture(initialFuture.ts_code);
          setDisplayedFutureCode(initialFuture.ts_code);
          setDisplayedFutureName(initialFuture.raw_name);
        }
      })
      .catch(error => {
        const errorMsg = '加载期货列表失败。';
        setError(errorMsg);
        console.error(errorMsg, error);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleFutureChange = (futureCode) => {
    const future = allFutures.find(f => f.ts_code === futureCode);
    if (future) {
      setSelectedFuture(future.ts_code);
      setDisplayedFutureCode(future.ts_code);
      setDisplayedFutureName(future.raw_name);
    }
  };

  const handleIntervalChange = (e) => {
    const newInterval = e.target.value;
    setSelectedInterval(newInterval);
  };

  return (
    <div>
      <Title level={4}>{title}</Title>
      <Text type="secondary">从列表中选择一个期货以查看其价格走势图。</Text>
      {error && <Text type="danger" style={{ display: 'block', marginTop: '10px' }}>{error}</Text>}
      <Card style={{ margin: '20px 0' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Select
              showSearch
              value={selectedFuture}
              placeholder={placeholder}
              style={{ width: 300 }}
              onChange={handleFutureChange}
              filterOption={(input, option) =>
                option.children.toLowerCase().includes(input.toLowerCase())
              }
            >
              {allFutures.map(future => (
                <Option key={future.ts_code} value={future.ts_code}>
                  {future.name}
                </Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Radio.Group value={selectedInterval} onChange={handleIntervalChange}>
              <Radio.Button value="daily">日线</Radio.Button>
              <Radio.Button value="weekly">周线</Radio.Button>
              <Radio.Button value="monthly">月线</Radio.Button>
            </Radio.Group>
          </Col>
        </Row>
      </Card>
      <Spin spinning={loading}>
        <StockChart
          chartData={chartData}
          stockCode={displayedFutureCode}
          stockName={displayedFutureName}
          interval={selectedInterval}
          corporateActions={null}
          showEvents={false}
        />
      </Spin>
    </div>
  );
};

export default FuturesDashboard;
