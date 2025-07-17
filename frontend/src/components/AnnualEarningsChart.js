import React, { useState, useEffect } from 'react';
import { Card, Typography, Slider, Spin, Alert } from 'antd';
import { Column } from '@ant-design/charts';

const { Title, Text } = Typography;

const AnnualEarningsChart = ({ data, loading, error }) => {
  const [filteredData, setFilteredData] = useState([]);
  const [yearRange, setYearRange] = useState([]);

  useEffect(() => {
    if (data && data.length > 0) {
      const years = data.map(item => item.year);
      const minYear = Math.min(...years);
      const maxYear = Math.max(...years);

      // Default to last 5 years or all if less than 5
      const defaultMinYear = Math.max(minYear, maxYear - 4); 
      setYearRange([defaultMinYear, maxYear]);
    }
  }, [data]);

  useEffect(() => {
    if (data && data.length > 0 && yearRange.length === 2) {
      const [startYear, endYear] = yearRange;
      const filtered = data.filter(item => item.year >= startYear && item.year <= endYear);
      setFilteredData(filtered);
    } else {
      setFilteredData([]);
    }
  }, [data, yearRange]);

  const config = {
    data: filteredData,
    xField: 'year',
    yField: 'net_profit',
    seriesField: 'year', // Color by year
    columnStyle: {
      radius: [20, 20, 0, 0],
    },
    meta: {
      net_profit: {
        formatter: (v) => v ?? 0,
      },
    },
    label: {
      position: 'top',
      style: {
        fill: '#FFFFFF',
        opacity: 0.6,
      },
    },
    tooltip: {
      formatter: (datum) => {
        const value = datum.net_profit ?? 0;
        return { name: '净利润', value: `${(value / 100000000).toFixed(2)} 亿元` };
      },
    },
    xAxis: {
      label: {
        autoHide: true,
        autoRotate: false,
      },
    },
    yAxis: {
      label: {
        formatter: (v) => `${(v / 100000000).toFixed(0)} 亿`,
      },
      title: {
        text: '净利润 (亿元)',
      },
    },
    interactions: [{ type: 'active-region', enable: false }],
    responsive: true,
  };

  if (loading) {
    return <Spin tip="加载年度盈利数据..." style={{ width: '100%', padding: '50px 0' }} />;
  }

  if (error) {
    return <Alert message="错误" description={error} type="error" showIcon />;
  }

  if (!data || data.length === 0) {
    return <Alert message="提示" description="暂无年度盈利数据。" type="info" showIcon />;
  }

  const years = data.map(item => item.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);

  return (
    <Card style={{ marginTop: '20px' }}>
      <Title level={5}>年度净利润</Title>
      <div style={{ marginBottom: '20px' }}>
        <Text>年份范围: {yearRange[0]} - {yearRange[1]}</Text>
        <Slider
          range
          min={minYear}
          max={maxYear}
          value={yearRange}
          onChange={setYearRange}
          marks={years.reduce((acc, year) => ({ ...acc, [year]: year }), {})}
          tooltip={{ 
            formatter: (value) => value ?? 0,
            open: true 
          }}
        />
      </div>
      <Column {...config} />
    </Card>
  );
};

export default AnnualEarningsChart;
