import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Select, message, Spin, Row, Col, Card, Typography, Radio, DatePicker, Switch } from 'antd';
import dayjs from 'dayjs';
import StockChart from '../components/StockChart';
import FinancialOverviewAndActions from '../components/FinancialOverviewAndActions';
import { getStockData, getAllStocks, getCorporateActions, getAnnualEarnings, getTopCryptos, getCryptoHistory } from '../api/stockApi';

const { Option } = Select;
const { Title, Text } = Typography;

const cryptoChineseNames = {
  BTC: '比特币',
  ETH: '以太坊',
  USDT: '泰达币',
  BNB: '币安币',
  SOL: '索拉纳',
  XRP: '瑞波币',
  USDC: '美元币',
  DOGE: '狗狗币',
  ADA: '艾达币',
  SHIB: '柴犬币',
  AVAX: '雪崩协议',
  TRX: '波场',
  DOT: '波卡',
  LINK: 'Chainlink',
  MATIC: 'Polygon',
  LTC: '莱特币',
  BCH: '比特币现金',
  UNI: 'Uniswap',
  XLM: '恒星币',
  ETC: '以太坊经典',
};

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

  const titleMap = {
    A_share: 'A股市场分析',
    US_stock: '美股市场分析',
    crypto: '加密货币行情',
  };
  const placeholderMap = {
    A_share: '搜索股票 (例如：600519.SH)',
    US_stock: '搜索或输入代码 (例如: AAPL)',
    crypto: '搜索或选择加密货币 (例如: BTC)',
  };

  const title = titleMap[marketType] || '市场分析';
  const placeholder = placeholderMap[marketType] || '搜索...';

  const fetchData = useCallback((stockCode, interval, date) => {
    if (!stockCode) return;
    if (debounceTimeout.current) clearTimeout(debounceTimeout.current);
    setLoading(true);
    setChartData([]);
    setError(null);

    debounceTimeout.current = setTimeout(() => {
      if (marketType === 'crypto') {
        getCryptoHistory(stockCode, interval)
          .then(response => {
            const formattedData = response.data.map(item => ({
              ...item, // Pass all existing properties (ma5, ma10, etc.)
              trade_date: dayjs.unix(item.time).format('YYYY-MM-DD'), // Format date
              vol: item.volumeto, // Rename volumeto to vol
            }));
            setChartData(formattedData);
          })
          .catch(error => {
            const errorMsg = error.response?.data?.detail || `加载 ${stockCode} 数据失败。`;
            setError(errorMsg);
            message.error(errorMsg);
            setChartData([]);
          })
          .finally(() => setLoading(false));
      } else {
        const dateStr = date ? date.format('YYYY-MM-DD') : null;
        getStockData(stockCode, interval, dateStr, marketType)
          .then(response => {
            // No special formatting needed, just pass the data through
            setChartData(response.data);
          })
          .catch(error => {
            const errorMsg = error.response?.data?.detail || `加载 ${stockCode} 数据失败。`;
            setError(errorMsg);
            message.error(errorMsg);
            setChartData([]);
          })
          .finally(() => setLoading(false));
      }
    }, 500);
  }, [marketType]);

  const fetchSecondaryData = useCallback((symbol) => {
    if (!symbol || marketType === 'crypto') return;

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

  // Effect to fetch all data when stock or interval changes
  useEffect(() => {
    if (selectedStock) {
      // Fetch main chart data
      fetchData(selectedStock, selectedInterval, selectedDate);

      // For non-crypto, fetch secondary data
      if (marketType !== 'crypto') {
        // Clear previous secondary data and errors
        setCorporateActions(null);
        setAnnualEarningsData([]);
        setActionsError(null);
        setAnnualEarningsError(null);
        // Fetch new secondary data
        fetchSecondaryData(selectedStock);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStock, selectedInterval]);

  // Initial data load effect when marketType changes
  useEffect(() => {
    setLoading(true);
    setAllStocks([]);
    setSelectedStock(null);
    setChartData([]);
    setDisplayedStockCode(null);
    setDisplayedStockName(null);
    setError(null);

    if (marketType === 'crypto') {
      getTopCryptos()
        .then(response => {
          const cryptos = response.data.map(crypto => {
            const symbol = crypto.CoinInfo.Name;
            const chineseName = cryptoChineseNames[symbol] || '';
            return {
              ts_code: symbol,
              name: `${crypto.CoinInfo.FullName}${chineseName ? ` (${chineseName})` : ''}`,
            };
          });
          setAllStocks(cryptos);
          if (cryptos.length > 0) {
            const initialStock = cryptos[0];
            setSelectedStock(initialStock.ts_code);
            setDisplayedStockCode(initialStock.ts_code);
            setDisplayedStockName(initialStock.name);
          }
        })
        .catch(error => {
          const errorMsg = '加载加密货币列表失败。';
          setError(errorMsg);
          console.error(errorMsg, error);
        })
        .finally(() => setLoading(false));
    } else {
      getAllStocks(marketType)
        .then(response => {
          const stocks = response.data;
          setAllStocks(stocks);
          if (stocks.length > 0) {
            const initialStock = stocks[0];
            setSelectedStock(initialStock.ts_code);
            setDisplayedStockCode(initialStock.ts_code);
            setDisplayedStockName(initialStock.name);
          }
        })
        .catch(error => {
          const errorMsg = `加载${marketType === 'A_share' ? 'A股' : '美股'}列表失败。`;
          setError(errorMsg);
          console.error(errorMsg, error);
        })
        .finally(() => setLoading(false));
    }
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
      <Text type="secondary">
        {marketType === 'crypto'
          ? '从列表中选择一个加密货币以查看其日线图。'
          : '选择一只股票和时间间隔以查看其图表。'}
      </Text>
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
              filterOption={(input, option) =>
                (option.children.toLowerCase().includes(input.toLowerCase()) ||
                  option.value.toLowerCase().includes(input.toLowerCase()))
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
              <Radio.Button value="minute" disabled={marketType === 'crypto'}>分时</Radio.Button>
              <Radio.Button value="5day" disabled={marketType === 'crypto'}>五日</Radio.Button>
              <Radio.Button value="daily">日线</Radio.Button>
              <Radio.Button value="weekly">周线</Radio.Button>
              <Radio.Button value="monthly">月线</Radio.Button>
            </Radio.Group>
          </Col>
          <Col>
            <DatePicker
              value={selectedDate}
              onChange={handleDateChange}
              disabled={!isDateSelectorEnabled || marketType === 'crypto'}
              allowClear={false}
            />
          </Col>
          <Col>
            <Switch
              checkedChildren="事件"
              unCheckedChildren="事件"
              checked={showEvents}
              onChange={setShowEvents}
              disabled={!isEventSwitchEnabled || marketType === 'crypto'}
            />
          </Col>
        </Row>
      </Card>
      <Spin spinning={loading}>
        {chartData.length > 0 && process.env.NODE_ENV === 'development' && console.log("Chart Data being passed to StockChart:", chartData.slice(-5))}
        <StockChart
          chartData={chartData}
          stockCode={displayedStockCode}
          stockName={displayedStockName}
          interval={selectedInterval}
          corporateActions={corporateActions}
          showEvents={showEvents}
        />
      </Spin>
      {marketType !== 'crypto' && (
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
      )}
    </div>
  );
};

export default Dashboard;
