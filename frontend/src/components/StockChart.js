import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

// Helper function to calculate the start percentage for the dataZoom component
const calculateStartPercent = (data, interval) => {
  if (!data || data.length === 0) {
    return { start: 0, end: 100 };
  }

  const totalPoints = data.length;
  let pointsToShow;

  switch (interval) {
    case 'daily':
      pointsToShow = 21 * 6; // Approx 6 months
      break;
    case 'weekly':
      pointsToShow = 52 * 2; // Approx 2 years
      break;
    case 'monthly':
    default:
      return { start: 0, end: 100 }; // Show all for monthly
  }

  if (totalPoints <= pointsToShow) {
    return { start: 0, end: 100 };
  }

  const startPercent = 100 - (pointsToShow / totalPoints) * 100;
  return { start: Math.max(0, startPercent), end: 100 };
};


// --- ECharts Option for K-Line (Daily, Weekly, Monthly) ---
const createKlineOption = (data, stockCode, stockName, interval) => {
  const dates = data.map(item => item.trade_date);
  const kData = data.map(item => [item.open, item.close, item.low, item.high]);
  const volumes = data.map((item, index) => [index, item.vol, item.open > item.close ? -1 : 1]);
  
  const maData = {};
  const maColors = { ma5: '#f5a623', ma10: '#4a90e2', ma20: '#bd10e0', ma60: '#50e3c2' };
  ['ma5', 'ma10', 'ma20', 'ma60'].forEach(ma => {
    if (data[0] && data[0][ma]) {
      maData[ma] = data.map(item => item[ma].toFixed(2));
    }
  });

  const zoom = calculateStartPercent(data, interval);
  const intervalMap = { daily: '日线', weekly: '周线', monthly: '月线' };
  const title = `${stockName} (${stockCode}) ${intervalMap[interval]} K线图`;

  return {
    title: { text: title, left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['K-Line', ...Object.keys(maData)], top: 30 },
    grid: [{ height: '50%' }, { top: '65%', height: '16%' }],
    xAxis: [
      { type: 'category', data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, splitLine: { show: false }, min: 'dataMin', max: 'dataMax' },
      { type: 'category', gridIndex: 1, data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false }, min: 'dataMin', max: 'dataMax' },
    ],
    yAxis: [
      { scale: true, splitArea: { show: true }, axisLabel: { formatter: val => val.toFixed(2) } },
      { scale: true, gridIndex: 1, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1], start: zoom.start, end: zoom.end }, { show: true, type: 'slider', xAxisIndex: [0, 1], top: '90%', start: zoom.start, end: zoom.end }],
    series: [
      { name: 'K-Line', type: 'candlestick', data: kData, itemStyle: { color: '#ef232a', color0: '#14b143', borderColor: '#ef232a', borderColor0: '#14b143' } },
      ...Object.keys(maData).map(ma => ({
        name: ma, type: 'line', data: maData[ma], smooth: true, showSymbol: false, lineStyle: { color: maColors[ma], width: 1 }
      })),
      { name: 'Volume', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes.map(item => item[1]), itemStyle: { color: ({dataIndex}) => volumes[dataIndex][2] === 1 ? '#ef232a' : '#14b143' } },
    ]
  };
};

// --- ECharts Option for Time-sharing (Minute, 5-Day) ---
const createTimeShareOption = (data, stockCode, stockName, interval) => {
  const dates = data.map(item => item.trade_date.substring(11, 16)); // Show HH:mm
  const prices = data.map(item => item.close);
  const avgPrices = data.map(item => item.avg_price);
  const volumes = data.map((item, index) => [index, item.vol, item.open > item.close ? -1 : 1]);
  const intervalMap = { minute: '分时图', '5day': '五日图' };
  const title = `${stockName} (${stockCode}) ${intervalMap[interval]}`;

  return {
    title: { text: title, left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['Price', 'Avg Price'], top: 30 },
    grid: [{ height: '50%' }, { top: '65%', height: '16%' }],
    xAxis: [
      { type: 'category', data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, splitLine: { show: false } },
      { type: 'category', gridIndex: 1, data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false } },
    ],
    yAxis: [
      { scale: true, splitArea: { show: true }, axisLabel: { formatter: val => val.toFixed(2) } },
      { scale: true, gridIndex: 1, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }, { show: true, type: 'slider', xAxisIndex: [0, 1], top: '90%' }],
    series: [
      { name: 'Price', type: 'line', data: prices, smooth: true, showSymbol: false, lineStyle: { color: '#4a90e2', width: 2 } },
      { name: 'Avg Price', type: 'line', data: avgPrices, smooth: true, showSymbol: false, lineStyle: { color: '#f5a623', width: 1 } },
      { name: 'Volume', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes.map(item => item[1]), itemStyle: { color: ({dataIndex}) => volumes[dataIndex][2] === 1 ? '#ef232a' : '#14b143' } },
    ]
  };
};


const StockChart = ({ chartData, stockCode, stockName, interval }) => {
  if (!chartData || chartData.length === 0) {
    return <Empty description="No data available for the selected stock or period." style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }} />;
  }

  let option;
  const isKline = ['daily', 'weekly', 'monthly'].includes(interval);

  try {
    if (isKline) {
      option = createKlineOption(chartData, stockCode, stockName, interval);
    } else {
      option = createTimeShareOption(chartData, stockCode, stockName, interval);
    }
  } catch (error) {
    console.error("Failed to create chart option:", error);
    return <Empty description="An error occurred while rendering the chart." style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }} />;
  }

  return <ReactECharts option={option} style={{ height: 500, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};

export default StockChart;
