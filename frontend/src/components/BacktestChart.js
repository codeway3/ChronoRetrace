import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

const BacktestChart = ({ klineData, portfolioData, transactions, stockCode, stockName, marketType = 'US_stock' }) => {
  if (!klineData || klineData.length === 0) {
    return <Empty description="无K线数据可供显示。" style={{ height: 500 }} />;
  }

  // 1. Prepare data for ECharts
  const dates = klineData.map(item => item.trade_date);
  const ohlcData = klineData.map(item => [item.open, item.close, item.low, item.high]);
  const volumes = klineData.map((item, index) => [index, item.vol, item.open > item.close ? -1 : 1]);
  
  const portfolioValues = portfolioData.map(item => item.portfolio_value.toFixed(2));
  const benchmarkValues = portfolioData.map(item => item.benchmark_value.toFixed(2));

  // 2. Create markers for buy/sell transactions
  const tradeMarkers = transactions.map(tx => {
    const dateIndex = dates.indexOf(tx.trade_date);
    if (dateIndex === -1) return null;
    
    const isBuy = tx.trade_type === 'buy';
    return {
      name: isBuy ? '买入' : '卖出',
      coord: [dateIndex, klineData[dateIndex].high * (isBuy ? 0.99 : 1.01)],
      value: tx.price.toFixed(2),
      symbol: isBuy ? 'arrow' : 'pin',
      symbolRotate: isBuy ? 180 : 0,
      symbolSize: 15,
      itemStyle: {
        color: isBuy ? '#28a745' : '#dc3545'
      },
      label: {
        show: true,
        position: isBuy ? 'below' : 'above',
        formatter: '{c}',
        color: '#fff',
        backgroundColor: isBuy ? '#28a745' : '#dc3545',
        padding: [2, 4],
        borderRadius: 2,
        fontSize: 10
      }
    };
  }).filter(Boolean);

  // 3. ECharts option configuration
  const option = {
    title: {
      text: `回测结果: ${stockName} (${stockCode})`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params) => {
        const date = params[0].axisValue;
        const currencySymbol = marketType === 'A_share' ? '¥' : '$';
        let tooltipText = `${date}<br/>`;
        params.forEach(p => {
          const { seriesName, value, marker } = p;
          if (seriesName === 'K线') {
            tooltipText += `${marker} 开: ${value[1]}, 收: ${value[2]}, 低: ${value[3]}, 高: ${value[4]}<br/>`;
          } else if (seriesName === '成交量') {
            tooltipText += `${marker} 成交量: ${(value / 10000).toFixed(2)}万<br/>`;
          } else {
            tooltipText += `${marker} ${seriesName}: ${currencySymbol}${(parseFloat(value)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}<br/>`;
          }
        });
        return tooltipText;
      }
    },
    legend: {
      data: ['K线', '策略价值', '基准价值'],
      top: 30
    },
    grid: [
      { height: '50%', right: '8%', left: '8%' },
      { top: '65%', height: '16%', right: '8%', left: '8%' } 
    ],
    xAxis: [
      { type: 'category', data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, splitLine: { show: false }, min: 'dataMin', max: 'dataMax' },
      { type: 'category', gridIndex: 1, data: dates, scale: true, boundaryGap: false, axisLine: { onZero: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false }, min: 'dataMin', max: 'dataMax' },
    ],
    yAxis: [
      { 
        name: '价格 (元)', 
        scale: true, 
        splitArea: { show: true }, 
        axisLabel: { formatter: val => val.toFixed(2) },
        position: 'left'
      },
      { 
        name: '成交量', 
        scale: true, 
        gridIndex: 1, 
        splitNumber: 2, 
        axisLabel: { show: false }, 
        axisLine: { show: false }, 
        axisTick: { show: false }, 
        splitLine: { show: false } 
      },
      { 
        name: '投资组合价值 (元)', 
        scale: true, 
        splitArea: { show: false },
        axisLabel: { formatter: val => `${(val / 10000).toFixed(1)}万` },
        position: 'right'
      }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
      { show: true, type: 'slider', xAxisIndex: [0, 1], top: '90%', start: 0, end: 100 }
    ],
    series: [
      { 
        name: 'K线', 
        type: 'candlestick', 
        yAxisIndex: 0,
        data: ohlcData, 
        itemStyle: { color: '#ef232a', color0: '#14b143', borderColor: '#ef232a', borderColor0: '#14b143' },
        markPoint: {
          data: tradeMarkers,
        }
      },
      { 
        name: '策略价值', 
        type: 'line', 
        yAxisIndex: 2,
        data: portfolioValues, 
        smooth: true, 
        showSymbol: false, 
        lineStyle: { color: '#f5a623', width: 2 }
      },
      { 
        name: '基准价值', 
        type: 'line', 
        yAxisIndex: 2,
        data: benchmarkValues, 
        smooth: true, 
        showSymbol: false, 
        lineStyle: { color: '#4a90e2', width: 2, type: 'dashed' }
      },
      { 
        name: '成交量', 
        type: 'bar', 
        xAxisIndex: 1, 
        yAxisIndex: 1, 
        data: volumes.map(item => item[1] ?? 0), 
        itemStyle: { color: ({ dataIndex }) => volumes[dataIndex]?.[2] === 1 ? '#ef232a' : '#14b143' } 
      },
    ]
  };

  return <ReactECharts option={option} style={{ height: 500, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};

export default BacktestChart;