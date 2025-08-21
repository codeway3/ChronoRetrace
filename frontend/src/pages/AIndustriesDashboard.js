import React, { useEffect, useState, useMemo } from 'react';
import { Card, Row, Col, Select, Table, Typography, Spin, Empty, message } from 'antd';
import ReactECharts from 'echarts-for-react';
import { getAIndustryOverview, getAIndustryStocks } from '../api/stockApi';

const { Option } = Select;
const { Title, Text } = Typography;

const SparklineChart = ({ data }) => {
  if (!data || data.length === 0) {
    return <span>-</span>;
  }

  const option = {
    grid: {
      left: 5,
      right: 5,
      top: 10,
      bottom: 10,
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.trade_date),
      show: false,
    },
    yAxis: {
      type: 'value',
      show: false,
      scale: true,
    },
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        const param = params[0];
        if (!param || param.value === undefined || param.value === null) {
          return '';
        }
        return `${param.axisValueLabel}: ${param.value.toFixed(2)}`;
      },
      axisPointer: {
        type: 'cross',
        label: {
          show: false,
        },
      },
    },
    series: [
      {
        data: data.map(item => item.close),
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: {
          width: 2,
        },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: '40px', width: '100%' }} />;
};

const mainColumns = [
  { title: '行业', dataIndex: 'industry_name', key: 'industry_name', width: 150, fixed: 'left' },
  { title: '代码', dataIndex: 'industry_code', key: 'industry_code', width: 100 },
  { title: '今日%', dataIndex: 'today_pct', key: 'today_pct', render: v => v == null ? '-' : (v.toFixed ? (v).toFixed(2)+'%' : `${v}%`), sorter: (a,b)=> (a.today_pct||0)-(b.today_pct||0), width: 100 },
  { title: '区间收益', dataIndex: 'ret_window', key: 'ret_window', render: v => v == null ? '-' : (v*100).toFixed(2)+'%', sorter: (a,b)=> (a.ret_window||0)-(b.ret_window||0), width: 120 },
  { title: '成交额(亿)', dataIndex: 'turnover', key: 'turnover', render: v => v == null ? '-' : (v/1e8).toFixed(1), sorter: (a,b)=> (a.turnover||0)-(b.turnover||0), width: 120 },
  { title: '价格趋势图', dataIndex: 'sparkline', key: 'sparkline', render: (arr) => <SparklineChart data={arr}/>, width: 250 },
];

const constituentColumns = [
  { title: '代码', dataIndex: 'stock_code', key: 'stock_code', width: 100 },
  { title: '名称', dataIndex: 'stock_name', key: 'stock_name', width: 120 },
  { title: '最新价', dataIndex: 'latest_price', key: 'latest_price', sorter: (a, b) => a.latest_price - b.latest_price, width: 100 },
  { title: '涨跌幅%', dataIndex: 'pct_change', key: 'pct_change', render: v => v == null ? '-' : `${v.toFixed(2)}%`, sorter: (a, b) => a.pct_change - b.pct_change, width: 100 },
  { title: '市盈率', dataIndex: 'pe_ratio', key: 'pe_ratio', sorter: (a, b) => a.pe_ratio - b.pe_ratio, width: 100 },
  { title: '换手率%', dataIndex: 'turnover_rate', key: 'turnover_rate', render: v => v == null ? '-' : `${v.toFixed(2)}%`, sorter: (a, b) => a.turnover_rate - b.turnover_rate, width: 100 },
];

export default function AIndustriesDashboard(){
  const [window, setWindow] = useState('20D');
  const [overview, setOverview] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const [expandedRowKey, setExpandedRowKey] = useState(null);
  const [constituentData, setConstituentData] = useState([]);
  const [constituentLoading, setConstituentLoading] = useState(false);

  useEffect(()=>{
    setLoading(true);
    getAIndustryOverview(window).then(res=> setOverview(res.data||[])).catch(err=>{
      message.error('加载行业总览失败');
    }).finally(()=> setLoading(false));
  },[window]);

  const sorted = useMemo(()=>{
    const safe = (v)=> (v==null || isNaN(v)) ? -Infinity : v;
    return [...overview].sort((a,b)=> safe(b.today_pct) - safe(a.today_pct));
  },[overview]);

  const handleExpand = (expanded, record) => {
    if (expanded) {
      setExpandedRowKey(record.industry_code);
      setConstituentLoading(true);
      getAIndustryStocks(record.industry_code)
        .then(res => {
          setConstituentData(res.data || []);
        })
        .catch(err => {
          message.error('加载成分股失败');
          setConstituentData([]);
        })
        .finally(() => {
          setConstituentLoading(false);
        });
    } else {
      setExpandedRowKey(null);
      setConstituentData([]);
    }
  };

  const expandedRowRender = () => {
    return (
      <Spin spinning={constituentLoading}>
        <Table
          columns={constituentColumns}
          dataSource={constituentData}
          rowKey="stock_code"
          pagination={{ pageSize: 10, size: 'small' }}
          size="small"
        />
      </Spin>
    );
  };

  return (
    <div>
      <Title level={4}>A股行业总览</Title>
      <Card style={{margin:'16px 0'}}>
        <Row gutter={16}>
          <Col>
            <Text>窗口</Text>
            <Select value={window} style={{width:120}} onChange={setWindow}>
              <Option value="5D">5日</Option>
              <Option value="20D">20日</Option>
              <Option value="60D">60日</Option>
            </Select>
          </Col>
        </Row>
      </Card>
      <Spin spinning={loading}>
        {sorted.length>0 ? (
          <Table
            columns={mainColumns}
            dataSource={sorted}
            rowKey="industry_code"
            size="small"
            pagination={{pageSize:20}}
            scroll={{ x: 840 }}
            expandable={{
              expandedRowRender,
              expandedRowKeys: expandedRowKey ? [expandedRowKey] : [],
              onExpand: handleExpand,
              expandRowByClick: true,
              // Only allow one row to be expanded at a time
              rowExpandable: record => true, 
            }}
          />
        ) : (
          <Empty description="暂无数据"/>
        )}
      </Spin>
    </div>
  )
}
