import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

const calculateStartPercent = (data, interval) => {
  if (!data || data.length === 0) return { start: 0, end: 100 };
  const totalPoints = data.length;
  let pointsToShow;
  switch (interval) {
    case 'daily': pointsToShow = 21 * 6; break;
    case 'weekly': pointsToShow = 52 * 2; break;
    default: return { start: 0, end: 100 };
  }
  if (totalPoints <= pointsToShow) return { start: 0, end: 100 };
  const startPercent = 100 - (pointsToShow / totalPoints) * 100;
  return { start: Math.max(0, startPercent), end: 100 };
};

const createKlineOption = (data, stockCode, stockName, interval, corporateActions, showEvents) => {
  const dates = data.map(item => item.trade_date);
  const kData = data.map(item => [item.open, item.close, item.low, item.high]);
  const volumes = data.map((item, index) => [index, item.vol, item.open > item.close ? -1 : 1]);
  
  const maData = {};
  const maColors = { ma5: '#f5a623', ma10: '#4a90e2', ma20: '#bd10e0', ma60: '#50e3c2' };
  ['ma5', 'ma10', 'ma20', 'ma60'].forEach(ma => {
    // Check if the key exists in the first data object, even if the value is null.
    // This confirms the backend is providing MA data.
    if (data[0] && ma in data[0]) {
      // Map the data, converting non-null values to a fixed format for the tooltip.
      // ECharts will correctly handle null/undefined values by creating gaps in the line.
      maData[ma] = data.map(item => item[ma] != null ? item[ma].toFixed(2) : null);
    }
  });

  const eventMarkers = [];
  if (showEvents && corporateActions && corporateActions.actions) {
    corporateActions.actions.forEach(action => {
      const dateIndex = dates.indexOf(action.ex_date);
      if (dateIndex > -1) {
        const isDividend = action.action_type === 'dividend';
        eventMarkers.push({
          name: isDividend ? '分红' : '拆股',
          coord: [dateIndex, data[dateIndex].high * 1.02], // Position marker slightly above the high
          value: isDividend ? `${action.value.toFixed(3)}` : `拆 ${action.value}:1`,
          symbol: isDividend ? 'pin' : 'diamond',
          symbolSize: 20,
          itemStyle: { color: isDividend ? '#28a745' : '#007bff' },
          label: { show: true, formatter: isDividend ? '股' : '拆', color: '#fff', fontSize: 10 }
        });
      }
    });
  }

  const zoom = calculateStartPercent(data, interval);
  const intervalMap = { daily: '日线', weekly: '周线', monthly: '月线' };
  const title = `${stockName} (${stockCode}) ${intervalMap[interval]} K线图`;

  const series = [
    { 
      name: 'K线', 
      type: 'candlestick', 
      data: kData, 
      itemStyle: { color: '#ef232a', color0: '#14b143', borderColor: '#ef232a', borderColor0: '#14b143' }
    },
    ...Object.keys(maData).map(ma => ({
      name: ma, type: 'line', data: maData[ma], smooth: true, showSymbol: false, lineStyle: { color: maColors[ma], width: 1 }
    })),
    { 
      name: '成交量', 
      type: 'bar', 
      xAxisIndex: 1, 
      yAxisIndex: 1, 
      data: volumes.map(item => item[1] ?? 0), 
      itemStyle: { color: ({ dataIndex }) => volumes[dataIndex]?.[2] === 1 ? '#ef232a' : '#14b143' } 
    },
  ];

  if (eventMarkers.length > 0) {
    series[0].markPoint = {
      symbolSize: 25,
      data: eventMarkers,
      tooltip: {
        formatter: (params) => `${params.name}<br/>${params.value}`
      }
    };
  }

  return {
    title: { text: title, left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['K线', ...Object.keys(maData)], top: 30 },
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
    series: series
  };
};

const createTimeShareOption = (data, stockCode, stockName, interval) => {
  const dates = data.map(item => item.trade_date.substring(11, 16));
  const prices = data.map(item => item.close);
  const avgPrices = data.map(item => item.avg_price);
  const volumes = data.map((item, index) => [index, item.vol, item.open > item.close ? -1 : 1]);
  const intervalMap = { minute: '分时图', '5day': '五日图' };
  const title = `${stockName} (${stockCode}) ${intervalMap[interval]}`;

  return {
    title: { text: title, left: 'center' },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['价格', '均价'], top: 30 },
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
      { name: '价格', type: 'line', data: prices, smooth: true, showSymbol: false, lineStyle: { color: '#4a90e2', width: 2 } },
      { name: '均价', type: 'line', data: avgPrices, smooth: true, showSymbol: false, lineStyle: { color: '#f5a623', width: 1 } },
      { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: volumes.map(item => item[1]), itemStyle: { color: ({dataIndex}) => volumes[dataIndex][2] === 1 ? '#ef232a' : '#14b143' } }
    ]
  };
};

const StockChart = ({ chartData, stockCode, stockName, interval, corporateActions, showEvents }) => {
  if (!chartData || chartData.length === 0) {
    return <Empty description="所选股票或周期无可用数据。" style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }} />;
  }

  let option;
  const isKline = ['daily', 'weekly', 'monthly'].includes(interval);

  try {
    if (isKline) {
      option = createKlineOption(chartData, stockCode, stockName, interval, corporateActions, showEvents);
    } else {
      option = createTimeShareOption(chartData, stockCode, stockName, interval);
    }
  } catch (error) {
    console.error("创建图表选项失败:", error);
    return <Empty description="渲染图表时发生错误。" style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }} />;
  }

  return <ReactECharts option={option} style={{ height: 500, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};

export default StockChart;
