import React, { useState, useEffect, useRef } from 'react';
import { Select, message, Spin, Row, Col, Card, Typography, Radio, DatePicker, Space } from 'antd';
import dayjs from 'dayjs';
import StockChart from '../components/StockChart';
import { getStockData, getDefaultStocks, getAllStocks } from '../api/stockApi';

const { Option } = Select;
const { Title, Text } = Typography;

const Dashboard = () => {
  const [allStocks, setAllStocks] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [displayedStockCode, setDisplayedStockCode] = useState(null);
  const [displayedStockName, setDisplayedStockName] = useState(null); // New state for stock name
  const [selectedInterval, setSelectedInterval] = useState('daily');
  const [selectedDate, setSelectedDate] = useState(dayjs()); // Default to today
  const debounceTimeout = useRef(null);

  // Fetch initial data (all stocks list and default stock)
  useEffect(() => {
    getAllStocks()
      .then(response => setAllStocks(response.data))
      .catch(error => {
        message.error('Failed to load stock list.');
        console.error('Failed to load stock list:', error);
      });

    getDefaultStocks()
      .then(response => {
        if (response.data.length > 0) {
          const initialStock = response.data[0];
          setSelectedStock(initialStock.ts_code);
          setDisplayedStockCode(initialStock.ts_code);
          setDisplayedStockName(initialStock.name); // Set initial name
          fetchData(initialStock.ts_code, 'daily', null); // Initial fetch is daily
        }
      })
      .catch(error => {
        message.error('Failed to load default stocks.');
        console.error(error);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchData = (stockCode, interval, date) => {
    if (!stockCode) {
      message.warning('Please select a stock.');
      return;
    }

    if (debounceTimeout.current) {
      clearTimeout(debounceTimeout.current);
    }

    setLoading(true);
    setChartData([]); // Clear previous data

    debounceTimeout.current = setTimeout(() => {
      // Format date to YYYY-MM-DD for the API call if it exists
      const dateStr = date ? date.format('YYYY-MM-DD') : null;

      getStockData(stockCode, interval, dateStr)
        .then(response => {
          setChartData(response.data);
        })
        .catch(error => {
          const errorMsg = error.response?.data?.detail || `Failed to load data for ${stockCode}.`;
          message.error(errorMsg);
          console.error(error);
          setChartData([]);
        })
        .finally(() => {
          setLoading(false);
        });
    }, 500);
  };

  const handleStockChange = (stockCode) => {
    const stock = allStocks.find(s => s.ts_code === stockCode);
    setSelectedStock(stockCode);
    setDisplayedStockCode(stockCode);
    if (stock) {
      setDisplayedStockName(stock.name);
    }
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
    // Only 'minute' and '5day' intervals are date-dependent
    if (['minute', '5day'].includes(selectedInterval)) {
      fetchData(selectedStock, selectedInterval, date);
    }
  };

  const isDateSelectorEnabled = ['minute', '5day'].includes(selectedInterval);

  return (
    <div>
      <Title level={4}>A-Share Market Analysis</Title>
      <Text type="secondary">Select a stock and a time interval to view its chart.</Text>
      
      <Card style={{ margin: '20px 0' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Select
              showSearch
              value={selectedStock}
              placeholder="Search for a stock (e.g., 600519.SH)"
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
        </Row>
      </Card>

      <Spin spinning={loading}>
        <StockChart 
          chartData={chartData} 
          stockCode={displayedStockCode}
          stockName={displayedStockName} 
          interval={selectedInterval} 
        />
      </Spin>
    </div>
  );
};

export default Dashboard;
