import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Select, message, Spin, Row, Col, Card, Typography, Radio } from 'antd';
import StockChart from '../components/StockChart';
import { getCommodityData, getCommodityList } from '../api/stockApi';

// 轻量重试与延迟工具
const sleep = (ms) => new Promise((res) => setTimeout(res, ms));
const retryAsync = async (fn, opts = {}) => {
  const { retries = 2, delay = 800, factor = 2 } = opts;
  let attempt = 0;
  let lastErr;
  while (attempt <= retries) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (attempt === retries) break;
      const wait = delay * Math.pow(factor, attempt);
      await sleep(wait);
    }
    attempt += 1;
  }
  throw lastErr;
};

const { Option } = Select;
const { Title, Text } = Typography;

const CommodityDashboard = () => {
  const [allCommodities, setAllCommodities] = useState([]);
  const [selectedCommodity, setSelectedCommodity] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [displayedCommodityCode, setDisplayedCommodityCode] = useState(null);
  const [displayedCommodityName, setDisplayedCommodityName] = useState(null);
  const [selectedInterval, setSelectedInterval] = useState('daily');
  const [error, setError] = useState(null);
  const debounceTimeout = useRef(null);
  const lastRequestIdRef = useRef(0);

  const title = '大宗商品市场';
  const placeholder = '搜索或选择大宗商品 (例如: GC=F)';

  const fetchData = useCallback((symbol, interval) => {
    if (!symbol) return;
    if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
    setLoading(true);
    setChartData([]);
    setError(null);

    debounceTimeout.current = setTimeout(() => {
      const reqId = Date.now();
      lastRequestIdRef.current = reqId;
      retryAsync(() => getCommodityData(symbol, interval), { retries: 1, delay: 800 })
        .then((response) => {
          if (lastRequestIdRef.current !== reqId) return;
          setChartData(response.data);
        })
        .catch((error) => {
          if (lastRequestIdRef.current !== reqId) return;
          const errorMsg = error.response?.data?.detail || `加载 ${symbol} 数据失败。`;
          setError(errorMsg);
          message.error(errorMsg);
          setChartData([]);
        })
        .finally(() => {
          if (lastRequestIdRef.current === reqId) setLoading(false);
        });
    }, 500);
  }, []);

  useEffect(() => {
    if (selectedCommodity) {
      fetchData(selectedCommodity, selectedInterval);
    }
  }, [selectedCommodity, selectedInterval, fetchData]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    retryAsync(() => getCommodityList(), { retries: 2, delay: 700 })
      .then((response) => {
        if (cancelled) return;
        const commodities = Object.entries(response.data).map(([symbol, name]) => ({
          ts_code: symbol,
          name: `${name} (${symbol})`,
          raw_name: name,
        }));
        setAllCommodities(commodities);
        // 移除自动选中第一个商品，保持默认未选中，等待用户主动选择
        // if (commodities.length > 0) {
        //   const initialCommodity = commodities[0];
        //   setSelectedCommodity(initialCommodity.ts_code);
        //   setDisplayedCommodityCode(initialCommodity.ts_code);
        //   setDisplayedCommodityName(initialCommodity.raw_name);
        // }
      })
      .catch((error) => {
        if (cancelled) return;
        const errorMsg = '加载大宗商品列表失败。';
        setError(errorMsg);
        message.error(errorMsg);
        // 重置状态，避免使用无效的历史选中值
        setAllCommodities([]);
        setSelectedCommodity(null);
        setDisplayedCommodityCode(null);
        setDisplayedCommodityName(null);
        console.error(errorMsg, error);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // 当当前选中的商品不在最新列表中时，自动重置为列表第一个合法项
  // useEffect(() => {
  //   if (allCommodities.length > 0) {
  //     const exists = allCommodities.some((c) => c.ts_code === selectedCommodity);
  //     if (!exists) {
  //       const initialCommodity = allCommodities[0];
  //       setSelectedCommodity(initialCommodity.ts_code);
  //       setDisplayedCommodityCode(initialCommodity.ts_code);
  //       setDisplayedCommodityName(initialCommodity.raw_name);
  //     }
  //   }
  // }, [allCommodities, selectedCommodity]);

  // 组件卸载时清理防抖与中断标记
  useEffect(() => {
    return () => {
      if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
      lastRequestIdRef.current += 1; // 失效旧请求
    };
  }, []);

  const handleCommodityChange = (commodityCode) => {
    const commodity = allCommodities.find((c) => c.ts_code === commodityCode);
    if (commodity) {
      setSelectedCommodity(commodity.ts_code);
      setDisplayedCommodityCode(commodity.ts_code);
      setDisplayedCommodityName(commodity.raw_name);
    }
  };

  const handleIntervalChange = (e) => {
    const newInterval = e.target.value;
    setSelectedInterval(newInterval);
  };

  return (
    <div>
      <Title level={4}>{title}</Title>
      <Text type="secondary">从列表中选择一个商品以查看其价格走势图。</Text>
      {error && (
        <Text type="danger" style={{ display: 'block', marginTop: '10px' }}>
          {error}
        </Text>
      )}
      <Card style={{ margin: '20px 0' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Select
              showSearch
              value={selectedCommodity}
              placeholder={placeholder}
              style={{ width: 300 }}
              onChange={handleCommodityChange}
              filterOption={(input, option) =>
                String(option.children).toLowerCase().includes(input.toLowerCase())
              }
            >
              {allCommodities.map((commodity) => (
                <Option key={commodity.ts_code} value={commodity.ts_code}>
                  {commodity.name}
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
          stockCode={displayedCommodityCode}
          stockName={displayedCommodityName}
          interval={selectedInterval}
          corporateActions={null}
          showEvents={false}
        />
      </Spin>
    </div>
  );
};

export default CommodityDashboard;
