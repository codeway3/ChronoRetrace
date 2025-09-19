import React, { useState } from 'react';
import { Card, Tabs, Row, Col, Statistic, Space, Tag, Button } from 'antd';
import {
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  BarChartOutlined,
  SearchOutlined,
  LineChartOutlined,
  DashboardOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import AssetScreener from '../components/AssetScreener';
import AssetBacktest from '../components/AssetBacktest';

const { TabPane } = Tabs;

const USStockPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  // 模拟美股市场数据
  const marketData = {
    totalStocks: 8500,
    upStocks: 4200,
    downStocks: 3100,
    unchangedStocks: 1200,
    totalMarketCap: '$45.2T',
    avgPE: 22.5,
    avgPB: 3.2,
    nasdaqIndex: 15234.56,
    sp500Index: 4567.89,
    dowIndex: 34567.12,
  };

  // 渲染仪表板
  const renderDashboard = () => (
    <div>
      {/* 主要指数 */}
      <Card title="主要指数" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <Statistic
              title="纳斯达克指数"
              value={marketData.nasdaqIndex}
              precision={2}
              valueStyle={{ color: '#f5222d' }}
              prefix={<RiseOutlined />}
              suffix="+1.2%"
            />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic
              title="标普500指数"
              value={marketData.sp500Index}
              precision={2}
              valueStyle={{ color: '#52c41a' }}
              prefix={<FallOutlined />}
              suffix="-0.8%"
            />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic
              title="道琼斯指数"
              value={marketData.dowIndex}
              precision={2}
              valueStyle={{ color: '#f5222d' }}
              prefix={<RiseOutlined />}
              suffix="+0.5%"
            />
          </Col>
        </Row>
      </Card>

      {/* 市场概览 */}
      <Card title="美股市场概览" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="总股票数"
              value={marketData.totalStocks}
              prefix={<DollarOutlined />}
              suffix="只"
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="上涨股票"
              value={marketData.upStocks}
              prefix={<RiseOutlined style={{ color: '#f5222d' }} />}
              suffix="只"
              valueStyle={{ color: '#f5222d' }}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="下跌股票"
              value={marketData.downStocks}
              prefix={<FallOutlined style={{ color: '#52c41a' }} />}
              suffix="只"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="平盘股票"
              value={marketData.unchangedStocks}
              suffix="只"
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="总市值"
              value={marketData.totalMarketCap}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="平均市盈率"
              value={marketData.avgPE}
              precision={1}
              suffix="倍"
            />
          </Col>
        </Row>
      </Card>

      {/* 热门板块 */}
      <Card title="热门板块" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Tag color="red">科技股 +2.8%</Tag>
          <Tag color="green">能源 -2.1%</Tag>
          <Tag color="blue">医疗保健 +1.5%</Tag>
          <Tag color="orange">金融 +0.9%</Tag>
          <Tag color="purple">消费品 -0.3%</Tag>
          <Tag color="cyan">工业 +1.1%</Tag>
          <Tag color="geekblue">电信 +0.4%</Tag>
          <Tag color="magenta">房地产 +1.7%</Tag>
        </Space>
      </Card>

      {/* 明星股票 */}
      <Card title="明星股票" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic
                title="AAPL"
                value={175.43}
                precision={2}
                prefix="$"
                suffix="+2.1%"
                valueStyle={{ color: '#f5222d' }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic
                title="MSFT"
                value={342.56}
                precision={2}
                prefix="$"
                suffix="+1.8%"
                valueStyle={{ color: '#f5222d' }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic
                title="GOOGL"
                value={2456.78}
                precision={2}
                prefix="$"
                suffix="-0.9%"
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small">
              <Statistic
                title="TSLA"
                value={234.12}
                precision={2}
                prefix="$"
                suffix="+3.5%"
                valueStyle={{ color: '#f5222d' }}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 快速操作 */}
      <Card title="快速操作">
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              size="large"
              block
              onClick={() => setActiveTab('screener')}
            >
              股票筛选
            </Button>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Button
              type="primary"
              icon={<BarChartOutlined />}
              size="large"
              block
              onClick={() => setActiveTab('backtest')}
            >
              策略回测
            </Button>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Button
              type="primary"
              icon={<LineChartOutlined />}
              size="large"
              block
            >
              技术分析
            </Button>
          </Col>
        </Row>
      </Card>
    </div>
  );

  return (
    <div className="us-stock-page">
      <Card
        title={
          <Space>
            <GlobalOutlined />
            <span>美股市场</span>
            <Tag color="processing">NYSE & NASDAQ</Tag>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} size="large">
          <TabPane
            tab={
              <span>
                <DashboardOutlined />
                市场概览
              </span>
            }
            key="dashboard"
          >
            {renderDashboard()}
          </TabPane>
          
          <TabPane
            tab={
              <span>
                <SearchOutlined />
                股票筛选
              </span>
            }
            key="screener"
          >
            <AssetScreener
              assetType="us_stock"
              title="美股筛选器"
            />
          </TabPane>
          
          <TabPane
            tab={
              <span>
                <BarChartOutlined />
                策略回测
              </span>
            }
            key="backtest"
          >
            <AssetBacktest
              assetType="us_stock"
              title="美股回测"
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default USStockPage;