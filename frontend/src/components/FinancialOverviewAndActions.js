import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { Spin, Card, Typography, Slider, Alert } from 'antd';
import './ActionsTimeline.css';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const FinancialOverviewAndActions = ({
  marketType,
  annualEarningsData,
  loadingAnnualEarnings,
  annualEarningsError,
  corporateActionsData,
  loadingCorporateActions,
  corporateActionsError,
}) => {
  const chartRef = useRef(null);

  const symbol = corporateActionsData?.symbol;
  const currencySymbol = marketType === 'US_stock' ? '$' : '¥';
  const currencyName = marketType === 'US_stock' ? '美元' : '元';

  const [yearRange, setYearRange] = useState([]);
  const [minOverallYear, setMinOverallYear] = useState(null);
  const [maxOverallYear, setMaxOverallYear] = useState(null);

  useEffect(() => {
    if ((!annualEarningsData || annualEarningsData.length === 0) && (!corporateActionsData || !corporateActionsData.actions || corporateActionsData.actions.length === 0)) {
      setMinOverallYear(null);
      setMaxOverallYear(null);
      setYearRange([]);
      return;
    }

    const allYears = new Set();
    annualEarningsData.forEach(item => allYears.add(item.year));
    if (corporateActionsData && corporateActionsData.actions) {
      corporateActionsData.actions.forEach(action => allYears.add(dayjs(action.ex_date).year()));
    }

    const sortedYears = Array.from(allYears).sort((a, b) => a - b);

    if (sortedYears.length > 0) {
      const minYear = sortedYears[0];
      const maxYear = sortedYears[sortedYears.length - 1];
      setMinOverallYear(minYear);
      setMaxOverallYear(maxYear);

      const defaultMinYear = Math.max(minYear, maxYear - 4);
      setYearRange([defaultMinYear, maxYear]);
    } else {
      setMinOverallYear(null);
      setMaxOverallYear(null);
      setYearRange([]);
    }
  }, [annualEarningsData, corporateActionsData]);

  useEffect(() => {
    if (!chartRef.current || !symbol || loadingAnnualEarnings || loadingCorporateActions || yearRange.length !== 2) return;

    const myChart = echarts.init(chartRef.current);
    const [startYear, endYear] = yearRange;

    const annualDividendsMap = {};
    if (corporateActionsData && corporateActionsData.actions) {
      corporateActionsData.actions.forEach(action => {
        if (action.action_type === 'dividend') {
          const year = dayjs(action.ex_date).year();
          if (year >= startYear && year <= endYear) {
            if (!annualDividendsMap[year]) {
              annualDividendsMap[year] = 0;
            }
            annualDividendsMap[year] += action.value;
          }
        }
      });
    }

    const filteredAnnualEarnings = annualEarningsData.filter(item => item.year >= startYear && item.year <= endYear);

    const years = Array.from(new Set([
      ...filteredAnnualEarnings.map(item => item.year),
      ...Object.keys(annualDividendsMap).map(Number)
    ])).sort((a, b) => a - b);

    const earningsData = years.map(year => {
      const earning = filteredAnnualEarnings.find(item => item.year === year);
      return earning ? earning.net_profit / 100000000 : null;
    });

    const dividendsData = years.map(year => annualDividendsMap[year] ?? null);

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params) => {
          let result = `${params[0].name}年<br/>`;
          params.forEach((item) => {
            if (item.seriesName === '净利润') {
              const value = item.value ?? 0;
              result += `${item.marker}${item.seriesName}: ${value !== null ? `${value.toFixed(2)}亿${currencyName}` : 'N/A'}<br/>`;
            } else if (item.seriesName === '年度分红') {
              const value = item.value ?? 0;
              result += `${item.marker}${item.seriesName}: ${value !== null ? `${currencySymbol}${value.toFixed(4)}` : 'N/A'}<br/>`;
            }
          });
          return result;
        }
      },
      legend: { data: ['净利润', '年度分红'] },
      xAxis: [{ type: 'category', data: years, axisPointer: { type: 'shadow' } }],
      yAxis: [
        { type: 'value', name: `净利润 (亿${currencyName})`, min: 0, axisLabel: { formatter: '{value}' } },
        { type: 'value', name: `年度分红 (${currencyName})`, min: 0, axisLabel: { formatter: '{value}' } }
      ],
      series: [
        { name: '净利润', type: 'bar', tooltip: { valueFormatter: (value) => `${value} 亿${currencyName}` }, data: earningsData },
        { name: '年度分红', type: 'line', yAxisIndex: 1, tooltip: { valueFormatter: (value) => value !== null && value !== undefined ? `${currencySymbol}${value.toFixed(4)}` : 'N/A' }, data: dividendsData }
      ]
    };

    myChart.setOption(option);

    return () => myChart.dispose();
  }, [symbol, annualEarningsData, corporateActionsData, loadingAnnualEarnings, loadingCorporateActions, yearRange, currencySymbol, currencyName]);

  const filteredGroupedActions = (corporateActionsData?.actions ?? []).reduce((acc, action) => {
    const year = dayjs(action.ex_date).year();
    if (year >= yearRange[0] && year <= yearRange[1]) {
      if (!acc[year]) acc[year] = [];
      acc[year].push(action);
    }
    return acc;
  }, {});

  const sortedYearsForTimeline = Object.keys(filteredGroupedActions).sort((a, b) => b - a);

  const isLoading = loadingAnnualEarnings || loadingCorporateActions;
  const hasError = annualEarningsError || corporateActionsError;
  const hasNoData = (!annualEarningsData || annualEarningsData.length === 0) && (!corporateActionsData || !corporateActionsData.actions || corporateActionsData.actions.length === 0) && !isLoading && !hasError;

  if (isLoading) return <div className="actions-timeline-container"><Spin tip="正在加载公司行动和盈利数据..."/></div>;
  if (hasError) return <div className="actions-timeline-container error">{annualEarningsError || corporateActionsError}</div>;
  if (hasNoData || minOverallYear === null) return <div className="actions-timeline-container"><Alert message="提示" description="暂无公司盈利或分红数据。" type="info" showIcon /></div>;

  return (
    <Card style={{ marginTop: '20px' }}>
      <Title level={5}>公司盈利与年度分红</Title>
      <div style={{ marginBottom: '20px' }}>
        <Text>年份范围: {yearRange[0]} - {yearRange[1]}</Text>
        <Slider
          range
          min={minOverallYear}
          max={maxOverallYear}
          value={yearRange}
          onChange={setYearRange}
          marks={(() => {
            const marks = {};
            if (minOverallYear === null || maxOverallYear === null) return marks;
            const totalYears = maxOverallYear - minOverallYear + 1;
            const labelInterval = totalYears <= 10 ? 1 : 5;
            for (let year = minOverallYear; year <= maxOverallYear; year++) {
              if ((year - minOverallYear) % labelInterval === 0 || year === minOverallYear || year === maxOverallYear) {
                marks[year] = year;
              } else {
                marks[year] = '';
              }
            }
            return marks;
          })()}
          tooltip={{ formatter: (value) => value }}
        />
      </div>
      <div ref={chartRef} style={{ width: '100%', height: '400px' }}></div>
      <h3 className="timeline-title" style={{marginTop: '20px'}}>分红历史</h3>
      <div className="timeline-scrollable-content">
        <div className="timeline">
          {sortedYearsForTimeline.map(year => (
            <React.Fragment key={year}>
              <div className="timeline-year-marker">{year}</div>
              {filteredGroupedActions[year].map(action => (
                <div key={action.id} className="timeline-item">
                  <div className="timeline-content">
                    <span className="action-date">{action.ex_date}</span>
                    <p className="action-description">
                      {`分红: ${currencySymbol}${action.value !== null && action.value !== undefined ? action.value.toFixed(4) : 'N/A'} 每股`}
                    </p>
                  </div>
                </div>
              ))}
            </React.Fragment>
          ))}
        </div>
      </div>
    </Card>
  );
};

export default FinancialOverviewAndActions;
