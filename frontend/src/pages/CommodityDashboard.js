import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Select, message, Spin, Row, Col, Card, Typography, Radio } from 'antd';
import StockChart from '../components/StockChart';
import { getCommodityData, getCommodityList } from '../api/stockApi';

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

  const title = '大宗商品市场';
  const placeholder = '搜索或选择大宗商品 (例如: GC=F)';

  const fetchData = useCallback((symbol, interval) => {
    if (!symbol) return;
    if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
    setLoading(true);
    setChartData([]);
    setError(null);

    debounceTimeout.current = setTimeout(() => {
      getCommodityData(symbol, interval)
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
    if (selectedCommodity) {
      fetchData(selectedCommodity, selectedInterval);
    }
  }, [selectedCommodity, selectedInterval, fetchData]);

  useEffect(() => {
    setLoading(true);
    getCommodityList()
      .then(response => {
        const commodities = Object.entries(response.data).map(([symbol, name]) => ({
          ts_code: symbol,
          name: `${name} (${symbol})`,
          raw_name: name,
        }));
        setAllCommodities(commodities);
        if (commodities.length > 0) {
          const initialCommodity = commodities[0];
          setSelectedCommodity(initialCommodity.ts_code);
          setDisplayedCommodityCode(initialCommodity.ts_code);
          setDisplayedCommodityName(initialCommodity.raw_name);
        }
      })
      .catch(error => {
        const errorMsg = '加载大宗商品列表失败。';
        setError(errorMsg);
        console.error(errorMsg, error);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleCommodityChange = (commodityCode) => {
    const commodity = allCommodities.find(c => c.ts_code === commodityCode);
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
      {error && <Text type="danger" style={{ display: 'block', marginTop: '10px' }}>{error}</Text>}
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
                option.children.toLowerCase().includes(input.toLowerCase())
              }
            >
              {allCommodities.map(commodity => (
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
