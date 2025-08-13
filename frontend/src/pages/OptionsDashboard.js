import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Input,
  Select,
  message,
  Spin,
  Row,
  Col,
  Card,
  Typography,
  Radio,
  Table,
  Tag,
  Empty,
  Button,
} from 'antd';
import StockChart from '../components/StockChart';
import { getOptionsData, getOptionExpirations, getOptionChain } from '../api/stockApi';

const { Option } = Select;
const { Title, Text } = Typography;

const OptionsDashboard = () => {
  const [underlyingSymbol, setUnderlyingSymbol] = useState('SPY');
  const [expirations, setExpirations] = useState([]);
  const [selectedExpiration, setSelectedExpiration] = useState(null);
  const [optionChain, setOptionChain] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [chartData, setChartData] = useState([]);
  
  const [loadingExpirations, setLoadingExpirations] = useState(false);
  const [loadingChain, setLoadingChain] = useState(false);
  const [loadingChart, setLoadingChart] = useState(false);
  
  const [selectedInterval, setSelectedInterval] = useState('daily');
  const [error, setError] = useState(null);
  const debounceTimeout = useRef(null);

  const fetchExpirations = useCallback((symbol) => {
    if (!symbol) return;
    setLoadingExpirations(true);
    setError(null);
    setExpirations([]);
    setSelectedExpiration(null);
    setOptionChain([]);
    setSelectedOption(null);
    setChartData([]);

    getOptionExpirations(symbol)
      .then(response => {
        setExpirations(response.data);
        if (response.data.length > 0) {
          setSelectedExpiration(response.data[0]);
        }
      })
      .catch(error => {
        const errorMsg = error.response?.data?.detail || `加载 ${symbol} 到期日失败。`;
        setError(errorMsg);
        message.error(errorMsg);
      })
      .finally(() => setLoadingExpirations(false));
  }, []);

  const fetchOptionChain = useCallback((symbol, expiration) => {
    if (!symbol || !expiration) return;
    setLoadingChain(true);
    setOptionChain([]);
    setSelectedOption(null);
    setChartData([]);

    getOptionChain(symbol, expiration)
      .then(response => {
        setOptionChain(response.data);
      })
      .catch(error => {
        const errorMsg = error.response?.data?.detail || `加载期权链失败。`;
        setError(errorMsg);
        message.error(errorMsg);
      })
      .finally(() => setLoadingChain(false));
  }, []);

  const fetchChartData = useCallback((symbol, interval) => {
    if (!symbol) return;
    setLoadingChart(true);
    setChartData([]);
    
    getOptionsData(symbol, interval)
      .then(response => {
        setChartData(response.data);
      })
      .catch(error => {
        const errorMsg = error.response?.data?.detail || `加载 ${symbol} 图表数据失败。`;
        setError(errorMsg);
        message.error(errorMsg);
      })
      .finally(() => setLoadingChart(false));
  }, []);

  // Initial load for default symbol
  useEffect(() => {
    fetchExpirations(underlyingSymbol);
  }, [fetchExpirations]);

  // Fetch chain when expiration changes
  useEffect(() => {
    if (underlyingSymbol && selectedExpiration) {
      fetchOptionChain(underlyingSymbol, selectedExpiration);
    }
  }, [underlyingSymbol, selectedExpiration, fetchOptionChain]);

  // Fetch chart when option or interval changes
  useEffect(() => {
    if (selectedOption) {
      fetchChartData(selectedOption.contract_symbol, selectedInterval);
    }
  }, [selectedOption, selectedInterval, fetchChartData]);

  const handleSymbolSearch = (symbol) => {
    if (symbol) {
      setUnderlyingSymbol(symbol.toUpperCase());
      fetchExpirations(symbol.toUpperCase());
    }
  };

  const columns = [
    { title: '类型', dataIndex: 'type', key: 'type', render: type => <Tag color={type === 'call' ? 'green' : 'volcano'}>{type.toUpperCase()}</Tag>, filters: [{text: 'Call', value: 'call'}, {text: 'Put', value: 'put'}], onFilter: (value, record) => record.type.indexOf(value) === 0 },
    { title: '代码', dataIndex: 'contract_symbol', key: 'contract_symbol', render: (text) => text, sorter: (a, b) => a.contract_symbol.localeCompare(b.contract_symbol) },
    { title: '行权价', dataIndex: 'strike', key: 'strike', sorter: (a, b) => a.strike - b.strike, defaultSortOrder: 'ascend' },
    { title: '最新价', dataIndex: 'last_price', key: 'last_price', sorter: (a, b) => a.last_price - b.last_price },
    { title: '买价', dataIndex: 'bid', key: 'bid', sorter: (a, b) => a.bid - b.bid },
    { title: '卖价', dataIndex: 'ask', key: 'ask', sorter: (a, b) => a.ask - b.ask },
    { title: '成交量', dataIndex: 'volume', key: 'volume', sorter: (a, b) => a.volume - b.volume },
    { title: '持仓量', dataIndex: 'open_interest', key: 'open_interest', sorter: (a, b) => a.open_interest - b.open_interest },
    { title: '隐含波动率', dataIndex: 'implied_volatility', key: 'implied_volatility', render: val => `${(val * 100).toFixed(2)}%`, sorter: (a, b) => a.implied_volatility - b.implied_volatility },
  ];

  return (
    <div>
      <Title level={4}>期权链分析</Title>
      <Text type="secondary">输入美股代码查询期权链，并点击合约查看K线图。</Text>
      {error && <Text type="danger" style={{ display: 'block', marginTop: '10px' }}>{error}</Text>}
      
      <Card style={{ margin: '20px 0' }}>
        <Row gutter={[16, 16]} align="bottom">
          <Col>
            <Text>股票代码</Text>
            <Input.Search
              placeholder="例如: SPY"
              defaultValue={underlyingSymbol}
              onSearch={handleSymbolSearch}
              style={{ width: 200, display: 'block' }}
              enterButton
            />
          </Col>
          <Col>
            <Text>到期日</Text>
            <Spin spinning={loadingExpirations}>
              <Select
                value={selectedExpiration}
                style={{ width: 200, display: 'block' }}
                onChange={setSelectedExpiration}
                disabled={loadingExpirations || expirations.length === 0}
              >
                {expirations.map(exp => <Option key={exp} value={exp}>{exp}</Option>)}
              </Select>
            </Spin>
          </Col>
          <Col>
            <Radio.Group value={selectedInterval} onChange={(e) => setSelectedInterval(e.target.value)}>
              <Radio.Button value="daily">日线</Radio.Button>
              <Radio.Button value="weekly">周线</Radio.Button>
              <Radio.Button value="monthly">月线</Radio.Button>
            </Radio.Group>
          </Col>
        </Row>
      </Card>

      <Title level={5}>期权链: {underlyingSymbol} @ {selectedExpiration}</Title>
      <Spin spinning={loadingChain}>
        <Table
          columns={columns}
          dataSource={optionChain}
          rowKey="contract_symbol"
          size="small"
          onRow={(record) => ({
            onClick: () => setSelectedOption(record),
          })}
          rowClassName={record => (record.contract_symbol === selectedOption?.contract_symbol ? 'ant-table-row-selected' : '')}
          locale={{ emptyText: <Empty description="没有找到期权数据，请尝试其他代码或到期日。" /> }}
          pagination={{ pageSize: 20 }}
        />
      </Spin>

      {selectedOption && (
        <div style={{ marginTop: '20px' }}>
          <Title level={5}>K线图: {selectedOption.contract_symbol}</Title>
          <Spin spinning={loadingChart}>
            <StockChart
              chartData={chartData}
              stockCode={selectedOption.contract_symbol}
              stockName={`${underlyingSymbol} ${selectedExpiration} ${selectedOption.strike} ${selectedOption.type.toUpperCase()}`}
              interval={selectedInterval}
              corporateActions={null}
              showEvents={false}
            />
          </Spin>
        </div>
      )}
    </div>
  );
};

export default OptionsDashboard;