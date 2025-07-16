import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Select, message, Spin, Row, Col, Card, Typography, Radio, DatePicker, Switch } from 'antd';
import dayjs from 'dayjs';
import StockChart from '../components/StockChart';

import FinancialOverviewAndActions from '../components/FinancialOverviewAndActions';
import { getStockData, getDefaultStocks, getAllStocks, getCorporateActions, getAnnualEarnings } from '../api/stockApi';

const { Option } = Select;
const { Title, Text } = Typography;

const Dashboard = () => {
  const [allStocks, setAllStocks] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [displayedStockCode, setDisplayedStockCode] = useState(null);
  const [displayedStockName, setDisplayedStockName] = useState(null);
  const [selectedInterval, setSelectedInterval] = useState('daily');
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const debounceTimeout = useRef(null);

  // New states for corporate actions
  const [corporateActions, setCorporateActions] = useState(null);
  const [loadingActions, setLoadingActions] = useState(false);
  const [actionsError, setActionsError] = useState(null);
  const [showEvents, setShowEvents] = useState(false); // State for the event markers switch

  // New states for annual earnings
  const [annualEarningsData, setAnnualEarningsData] = useState([]);
  const [loadingAnnualEarnings, setLoadingAnnualEarnings] = useState(false);
  const [annualEarningsError, setAnnualEarningsError] = useState(null);


  const fetchData = useCallback((stockCode, interval, date) => {
    if (!stockCode) return;
    if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
    setLoading(true);
    setChartData([]);
    debounceTimeout.current = setTimeout(() => {
      const dateStr = date ? date.format('YYYY-MM-DD') : null;
      getStockData(stockCode, interval, dateStr)
        .then(response => setChartData(response.data))
        .catch(error => {
          const errorMsg = error.response?.data?.detail || `加载 ${stockCode} 数据失败。`;
          message.error(errorMsg);
          setChartData([]);
        })
        .finally(() => setLoading(false));
    }, 500);
  }, []);

  // Effect for fetching fundamental and corporate action data
  useEffect(() => {
    if (!selectedStock) return;

    // Extract the base symbol (e.g., "000001") from the full ts_code ("000001.SZ")
    const baseSymbol = selectedStock.split('.')[0];

    setCorporateActions(null);
    setActionsError(null);

    setLoadingActions(true);
    getCorporateActions(baseSymbol)
      .then(response => setCorporateActions(response.data))
      .catch(error => setActionsError(error.response?.data?.detail || 'Failed to load actions.'))
      .finally(() => setLoadingActions(false));

  }, [selectedStock]);

  // Effect for fetching annual earnings data
  useEffect(() => {
    if (!selectedStock) return;

    const baseSymbol = selectedStock.split('.')[0];

    setAnnualEarningsData([]);
    setAnnualEarningsError(null);
    setLoadingAnnualEarnings(true);

    getAnnualEarnings(baseSymbol)
      .then(response => {
        // Sort data by year in ascending order for chart display
        const sortedData = response.data.sort((a, b) => a.year - b.year);
        setAnnualEarningsData(sortedData);
      })
      .catch(error => setAnnualEarningsError(error.response?.data?.detail || 'Failed to load annual earnings.'))
      .finally(() => setLoadingAnnualEarnings(false));
  }, [selectedStock]);


  // Initial data load effect
  useEffect(() => {
    getAllStocks()
      .then(response => setAllStocks(response.data))
      .catch(error => message.error('加载股票列表失败。'));

    getDefaultStocks()
      .then(response => {
        if (response.data.length > 0) {
          const initialStock = response.data[0];
          setSelectedStock(initialStock.ts_code);
          setDisplayedStockCode(initialStock.ts_code);
          setDisplayedStockName(initialStock.name);
          fetchData(initialStock.ts_code, 'daily', null);
        }
      })
      .catch(error => message.error('加载默认股票失败。'));
  }, [fetchData]);

  const handleStockChange = (stockCode) => {
    const stock = allStocks.find(s => s.ts_code === stockCode);
    setSelectedStock(stockCode);
    setDisplayedStockCode(stockCode);
    if (stock) setDisplayedStockName(stock.name);
    fetchData(stockCode, selectedInterval, selectedDate);
  };

  const handleIntervalChange = (e) => {
    const newInterval = e.target.value;
    setSelectedInterval(newInterval);
    fetchData(selectedStock, newInterval, selectedDate);
  };

  const handleDateChange = (date) => {
    if (!date) return;
    setSelectedDate(date);
    if (['minute', '5day'].includes(selectedInterval)) {
      fetchData(selectedStock, selectedInterval, date);
    }
  };

  const isDateSelectorEnabled = ['minute', '5day'].includes(selectedInterval);
  const isEventSwitchEnabled = ['daily', 'weekly', 'monthly'].includes(selectedInterval);

  return (
    <div>
      <Title level={4}>A股市场分析</Title>
      <Text type="secondary">选择一只股票和时间间隔以查看其图表。</Text>
      
      <Card style={{ margin: '20px 0' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Select
              showSearch
              value={selectedStock}
              placeholder="搜索股票 (例如：600519.SH)"
              style={{ width: 300 }}
              onChange={handleStockChange}
              filterOption={(input, option) =>
                option.children.toLowerCase().includes(input.toLowerCase()) ||
                option.value.toLowerCase().includes(input.toLowerCase())
              }
            >
              {allStocks.map(stock => (
                <Option key={stock.ts_code} value={stock.ts_code}>
                  {`${stock.name} (${stock.ts_code})`}
                </Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Radio.Group value={selectedInterval} onChange={handleIntervalChange}>
              <Radio.Button value="minute">分时</Radio.Button>
              <Radio.Button value="5day">五日</Radio.Button>
              <Radio.Button value="daily">日线</Radio.Button>
              <Radio.Button value="weekly">周线</Radio.Button>
              <Radio.Button value="monthly">月线</Radio.Button>
            </Radio.Group>
          </Col>
          <Col>
            <DatePicker 
              value={selectedDate} 
              onChange={handleDateChange} 
              disabled={!isDateSelectorEnabled}
              allowClear={false}
            />
          </Col>
          <Col>
            <Switch
              checkedChildren="事件"
              unCheckedChildren="事件"
              checked={showEvents}
              onChange={setShowEvents}
              disabled={!isEventSwitchEnabled}
            />
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading}>
        <StockChart 
          chartData={chartData} 
          stockCode={displayedStockCode}
          stockName={displayedStockName} 
          interval={selectedInterval}
          corporateActions={corporateActions}
          showEvents={showEvents}
        />
      </Spin>

      {/* Render Financial Overview and Actions */}
      <div className="deep-dive-container" style={{marginTop: '20px'}}>
          <FinancialOverviewAndActions 
            annualEarningsData={annualEarningsData}
            loadingAnnualEarnings={loadingAnnualEarnings}
            annualEarningsError={annualEarningsError}
            corporateActionsData={corporateActions}
            loadingCorporateActions={loadingActions}
            corporateActionsError={actionsError}
          />
      </div>
    </div>
  );
};

export default Dashboard;
