import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Select, message, Spin, Row, Col, Card, Typography, Radio, DatePicker, Switch } from 'antd';
import dayjs from 'dayjs';
import StockChart from '../components/StockChart';
import FinancialOverviewAndActions from '../components/FinancialOverviewAndActions';
import { getStockData, getAllStocks, getCorporateActions, getAnnualEarnings } from '../api/stockApi';

const { Option } = Select;
const { Title, Text } = Typography;

const Dashboard = ({ marketType }) => {
  const [allStocks, setAllStocks] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [displayedStockCode, setDisplayedStockCode] = useState(null);
  const [displayedStockName, setDisplayedStockName] = useState(null);
  const [selectedInterval, setSelectedInterval] = useState('daily');
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [error, setError] = useState(null); // 新增错误状态
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

  const title = marketType === 'A_share' ? 'A股市场分析' : '美股市场分析';
  const placeholder = marketType === 'A_share' ? '搜索股票 (例如：600519.SH)' : '搜索或输入代码 (例如: AAPL)';

  const fetchData = useCallback((stockCode, interval, date) => {
    if (!stockCode) return;
    if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
    setLoading(true);
    setChartData([]);
    debounceTimeout.current = setTimeout(() => {
      const dateStr = date ? date.format('YYYY-MM-DD') : null;
      getStockData(stockCode, interval, dateStr, marketType)
        .then(response => setChartData(response.data))
        .catch(error => {
          const errorMsg = error.response?.data?.detail || `加载 ${stockCode} 数据失败。`;
          setError(errorMsg); // 使用状态记录错误
          message.error(errorMsg);
          setChartData([]);
        })
        .finally(() => setLoading(false));
    }, 500);
  }, [marketType]);

  const fetchSecondaryData = useCallback((symbol) => {
    if (!symbol) return;

    const baseSymbol = marketType === 'A_share' ? symbol.split('.')[0] : symbol;

    // Fetch Corporate Actions
    setLoadingActions(true);
    getCorporateActions(baseSymbol)
      .then(response => {
        if (response.status === 202) {
          setActionsError('分红数据正在同步中，请稍后刷新页面获取。');
        } else {
          setCorporateActions(response.data);
          setActionsError(null);
        }
      })
      .catch(error => {
        setActionsError(error.response?.data?.detail || 'Failed to load actions.');
      })
      .finally(() => setLoadingActions(false));

    // Fetch Annual Earnings
    setLoadingAnnualEarnings(true);
    getAnnualEarnings(baseSymbol)
      .then(response => {
        if (response.status === 202) {
          setAnnualEarningsError('年报数据正在同步中，请稍后刷新页面获取。');
        } else {
          const sortedData = response.data.sort((a, b) => a.year - b.year);
          setAnnualEarningsData(sortedData);
          setAnnualEarningsError(null);
        }
      })
      .catch(error => {
        setAnnualEarningsError(error.response?.data?.detail || 'Failed to load annual earnings.');
      })
      .finally(() => {
        setLoadingAnnualEarnings(false);
      });
  }, [marketType]);

  // Effect to fetch all data when stock changes
  useEffect(() => {
    if (selectedStock) {
      // Fetch main chart data
      fetchData(selectedStock, selectedInterval, selectedDate);

      // Clear previous secondary data and errors
      setCorporateActions(null);
      setAnnualEarningsData([]);
      setActionsError(null);
      setAnnualEarningsError(null);

      // Fetch new secondary data
      fetchSecondaryData(selectedStock);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStock]);

  // Initial data load effect when marketType changes
  useEffect(() => {
    setLoading(true);
    setAllStocks([]);
    setSelectedStock(null);
    setChartData([]);
    setDisplayedStockCode(null);
    setDisplayedStockName(null);
    setError(null); // 重置错误状态

    getAllStocks(marketType)
      .then(response => {
        const stocks = response.data;
        setAllStocks(stocks);
        const initialStock = stocks[0];
        if (initialStock) {
          setSelectedStock(initialStock.ts_code);
          setDisplayedStockCode(initialStock.ts_code);
          setDisplayedStockName(initialStock.name);
        }
      })
      .catch(error => {
        const errorMsg = `加载${marketType === 'A_share' ? 'A股' : '美股'}列表失败。`;
        setError(errorMsg); // 使用状态记录错误
        console.error(errorMsg, error); // 记录日志代替 message.error
      })
      .finally(() => setLoading(false));
  }, [marketType]);

  const handleStockChange = (stockCode) => {
    let stock = allStocks.find(s => s.ts_code === stockCode);

    if (!stock && marketType === 'US_stock') {
      const newStock = { ts_code: stockCode, name: stockCode };
      setAllStocks(prev => [newStock, ...prev.filter(s => s.ts_code !== stockCode)]);
      stock = newStock;
    }

    if (stock) {
      setSelectedStock(stock.ts_code);
      setDisplayedStockCode(stock.ts_code);
      setDisplayedStockName(stock.name);
    }
  };

  const handleIntervalChange = (e) => {
    const newInterval = e.target.value;
    setSelectedInterval(newInterval);
    if (selectedStock) {
      fetchData(selectedStock, newInterval, selectedDate);
    }
  };

  const handleDateChange = (date) => {
    if (!date) return;
    setSelectedDate(date);
    if (['minute', '5day'].includes(selectedInterval) && selectedStock) {
      fetchData(selectedStock, selectedInterval, date);
    }
  };

  const isDateSelectorEnabled = ['minute', '5day'].includes(selectedInterval);
  const isEventSwitchEnabled = ['daily', 'weekly', 'monthly'].includes(selectedInterval);

  return (
    <div>
      <Title level={4}>{title}</Title>
      <Text type="secondary">选择一只股票和时间间隔以查看其图表。</Text>
      {error && <Text type="danger">{error}</Text>} {/* 显示错误信息 */}
      <Card style={{ margin: '20px 0' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Select
              showSearch
              value={selectedStock}
              placeholder={placeholder}
              style={{ width: 300 }}
              onChange={handleStockChange}
              filterOption={marketType === 'A_share'
                ? (input, option) =>
                (option.children.toLowerCase().includes(input.toLowerCase()) ||
                  option.value.toLowerCase().includes(input.toLowerCase()))
                : false
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
      <div className="deep-dive-container" style={{ marginTop: '20px' }}>
        <FinancialOverviewAndActions
          marketType={marketType}
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