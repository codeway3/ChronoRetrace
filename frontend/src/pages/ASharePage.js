import React, { useState } from 'react';
import { Card, Tabs, Row, Col, Statistic, Space, Tag, Button } from 'antd';
import {
  StockOutlined,
  RiseOutlined,
  FallOutlined,
  BarChartOutlined,
  SearchOutlined,
  LineChartOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import AssetScreener from '../components/AssetScreener';
import AssetBacktest from '../components/AssetBacktest';

const { TabPane } = Tabs;

const ASharePage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  // 模拟市场数据
  const marketData = {
    totalStocks: 4800,
    upStocks: 2100,
    downStocks: 1950,
    unchangedStocks: 750,
    totalMarketCap: '85.6万亿',
    avgPE: 15.8,
    avgPB: 1.45,
  };

  // 渲染仪表板
  const renderDashboard = () => (
    <div>
      {/* 市场概览 */}
      <Card title="A股市场概览" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="总股票数"
              value={marketData.totalStocks}
              prefix={<StockOutlined />}
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
              prefix="¥"
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
          <Tag color="red">新能源汽车 +3.2%</Tag>
          <Tag color="green">半导体 -1.8%</Tag>
          <Tag color="blue">医药生物 +0.9%</Tag>
          <Tag color="orange">白酒 +2.1%</Tag>
          <Tag color="purple">银行 -0.5%</Tag>
          <Tag color="cyan">房地产 +1.3%</Tag>
          <Tag color="geekblue">5G通信 +0.7%</Tag>
          <Tag color="magenta">新材料 +1.9%</Tag>
        </Space>
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
    <div className="a-share-page">
      <Card
        title={
          <Space>
            <StockOutlined />
            <span>A股市场</span>
            <Tag color="processing">沪深A股</Tag>
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
              assetType="a_share"
              title="A股筛选器"
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
              assetType="a_share"
              title="A股回测"
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default ASharePage;
