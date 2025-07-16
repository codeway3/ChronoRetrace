import React, { useEffect, useRef, useState } from 'react';
import * as echarts from 'echarts';
import { Spin, Card, Typography, Slider, Alert } from 'antd';
import './ActionsTimeline.css';
import dayjs from 'dayjs'; // Import dayjs

const { Title, Text } = Typography;

const FinancialOverviewAndActions = ({
  annualEarningsData,
  loadingAnnualEarnings,
  annualEarningsError,
  corporateActionsData,
  loadingCorporateActions,
  corporateActionsError,
}) => {
  const chartRef = useRef(null);

  const symbol = corporateActionsData?.symbol; // Adjusted to use corporateActionsData.symbol

  // New states for year range control
  const [yearRange, setYearRange] = useState([]);
  const [minOverallYear, setMinOverallYear] = useState(null);
  const [maxOverallYear, setMaxOverallYear] = useState(null);

  // Effect to determine overall year range and set initial slider range
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
      corporateActionsData.actions.forEach(action => allYears.add(dayjs(action.ex_date).year())); // Use dayjs
    }

    const sortedYears = Array.from(allYears).sort((a, b) => a - b);

    if (sortedYears.length > 0) {
      const minYear = sortedYears[0];
      const maxYear = sortedYears[sortedYears.length - 1];
      setMinOverallYear(minYear);
      setMaxOverallYear(maxYear);

      // Default to last 5 years or all if less than 5
      const defaultMinYear = Math.max(minYear, maxYear - 4);
      setYearRange([defaultMinYear, maxYear]);
    } else {
      setMinOverallYear(null);
      setMaxOverallYear(null);
      setYearRange([]);
    }
  }, [annualEarningsData, corporateActionsData]);


  // Prepare chart data and render ECharts
  useEffect(() => {
    // Update conditions: use new loading states, and check for valid yearRange
    if (!chartRef.current || !symbol || loadingAnnualEarnings || loadingCorporateActions || yearRange.length !== 2) return;

    const myChart = echarts.init(chartRef.current);

    const [startYear, endYear] = yearRange;

    // Calculate annual total dividends, filtered by yearRange
    const annualDividendsMap = {};
    if (corporateActionsData && corporateActionsData.actions) {
      corporateActionsData.actions.forEach(action => {
        if (action.action_type === 'dividend') {
          const year = dayjs(action.ex_date).year(); // Use dayjs
          if (year >= startYear && year <= endYear) { // Filter by yearRange
            if (!annualDividendsMap[year]) {
              annualDividendsMap[year] = 0;
            }
            annualDividendsMap[year] += action.value;
          }
        }
      });
    }

    // Filter annual earnings by yearRange
    const filteredAnnualEarnings = annualEarningsData.filter(item => item.year >= startYear && item.year <= endYear);

    const years = Array.from(new Set([
      ...filteredAnnualEarnings.map(item => item.year),
      ...Object.keys(annualDividendsMap).map(Number)
    ])).sort((a, b) => a - b);

    const earningsData = years.map(year => {
      const earning = filteredAnnualEarnings.find(item => item.year === year);
      return earning ? earning.net_profit / 100000000 : null; // Convert to hundreds of millions
    });

    const dividendsData = years.map(year => {
      return annualDividendsMap[year] ? annualDividendsMap[year] : null;
    });

    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: function (params) {
          let result = params[0].name + '年<br/>';
          params.forEach(function (item) {
            if (item.seriesName === '净利润') {
              result += item.marker + item.seriesName + ': ' + (item.value !== null ? item.value.toFixed(2) + '亿' : 'N/A') + '<br/>';
            } else if (item.seriesName === '年度分红') {
              result += item.marker + item.seriesName + ': ' + (item.value !== null ? '¥' + item.value.toFixed(4) : 'N/A') + '<br/>';
            }
          });
          return result;
        }
      },
      legend: {
        data: ['净利润', '年度分红']
      },
      xAxis: [
        {
          type: 'category',
          data: years,
          axisPointer: {
            type: 'shadow'
          }
        }
      ],
      yAxis: [
        {
          type: 'value',
          name: '净利润 (亿)',
          min: 0,
          axisLabel: {
            formatter: '{value}'
          }
        },
        {
          type: 'value',
          name: '年度分红 (元)',
          min: 0,
          axisLabel: {
            formatter: '{value}'
          }
        }
      ],
      series: [
        {
          name: '净利润',
          type: 'bar',
          tooltip: { valueFormatter: function (value) { return value + ' 亿'; } },
          data: earningsData
        },
        {
          name: '年度分红',
          type: 'line',
          yAxisIndex: 1,
          tooltip: { valueFormatter: function (value) { return '¥' + value.toFixed(4); } },
          data: dividendsData
        }
      ]
    };

    myChart.setOption(option);

    return () => {
      myChart.dispose();
    };
  }, [symbol, annualEarningsData, corporateActionsData, loadingAnnualEarnings, loadingCorporateActions, yearRange]);

  // Filtered grouped actions for the timeline list
  const filteredGroupedActions = (corporateActionsData && corporateActionsData.actions)
    ? corporateActionsData.actions.reduce((acc, action) => {
        const year = dayjs(action.ex_date).year(); // Use dayjs
        if (year >= yearRange[0] && year <= yearRange[1]) { // Filter by yearRange
          if (!acc[year]) {
            acc[year] = [];
          }
          acc[year].push(action);
        }
        return acc;
      }, {})
    : {};

  // Sort years in descending order for the timeline list
  const sortedYearsForTimeline = Object.keys(filteredGroupedActions).sort((a, b) => b - a);

  const isLoading = loadingAnnualEarnings || loadingCorporateActions;
  const hasError = annualEarningsError || corporateActionsError;
  const hasNoData = (!annualEarningsData || annualEarningsData.length === 0) && (!corporateActionsData || !corporateActionsData.actions || corporateActionsData.actions.length === 0) && !isLoading && !hasError;

  if (isLoading) {
    return <div className="actions-timeline-container"><Spin tip="正在加载公司行动和盈利数据..."></Spin></div>;
  }
  if (hasError) {
    return <div className="actions-timeline-container error">{annualEarningsError || corporateActionsError}</div>;
  }
  if (hasNoData || minOverallYear === null) {
    return <div className="actions-timeline-container"><Alert message="提示" description="暂无公司盈利或分红数据。" type="info" showIcon /></div>;
  }

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
            const labelInterval = totalYears <= 10 ? 1 : 5; // Show every year if <=10 years, else every 5 years

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
      <h3 className="timeline-title" style={{marginTop: '20px'}}>分红与拆股历史</h3>
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
                    {action.action_type === 'dividend'
                      ? `分红: ¥${action.value.toFixed(4)} 每股`
                      : `拆股: ${action.value.toFixed(2)} 股拆 1`}
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