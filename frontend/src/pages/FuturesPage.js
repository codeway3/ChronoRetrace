import React, { useState } from 'react';
import { Card, Tabs, Row, Col, Statistic, Space, Tag, Button, Alert } from 'antd';
import {
  FundOutlined,
  RiseOutlined,
  FallOutlined,
  BarChartOutlined,
  SearchOutlined,
  LineChartOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  FireOutlined,
} from '@ant-design/icons';
import AssetScreener from '../components/AssetScreener';
import AssetBacktest from '../components/AssetBacktest';

const { TabPane } = Tabs;

const FuturesPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  // 模拟期货市场数据
  const marketData = {
    totalContracts: 450,
    upContracts: 180,
    downContracts: 220,
    unchangedContracts: 50,
    totalVolume: '2.8万亿',
    totalOpenInterest: '1.2万亿',
    avgVolatility: 15.8,
  };

  // 主要期货合约数据
  const majorFutures = [
    { symbol: 'IF2312', name: '沪深300主力', price: 3856.2, change: 1.8, volume: '125万手' },
    { symbol: 'IC2312', name: '中证500主力', price: 5234.8, change: -0.9, volume: '89万手' },
    { symbol: 'IH2312', name: '上证50主力', price: 2567.4, change: 2.1, volume: '67万手' },
    { symbol: 'T2312', name: '10年国债主力', price: 102.45, change: 0.3, volume: '45万手' },
    { symbol: 'TF2312', name: '5年国债主力', price: 101.23, change: -0.1, volume: '32万手' },
    { symbol: 'TS2312', name: '2年国债主力', price: 100.89, change: 0.2, volume: '28万手' },
  ];

  // 商品期货数据
  const commodityFutures = [
    { symbol: 'CU2312', name: '沪铜主力', price: 68450, change: 2.3, category: '有色金属' },
    { symbol: 'AL2312', name: '沪铝主力', price: 18920, change: -1.1, category: '有色金属' },
    { symbol: 'RB2312', name: '螺纹钢主力', price: 3890, change: 1.5, category: '黑色金属' },
    { symbol: 'HC2312', name: '热卷主力', price: 3720, change: 0.8, category: '黑色金属' },
    { symbol: 'C2312', name: '玉米主力', price: 2856, change: -0.5, category: '农产品' },
    { symbol: 'M2312', name: '豆粕主力', price: 3245, change: 1.2, category: '农产品' },
  ];

  // 渲染仪表板
  const renderDashboard = () => (
    <div>
      {/* 风险提示 */}
      <Alert
        message="期货交易风险提示"
        description="期货交易具有高杠杆、高风险特征，可能导致本金全部损失，请充分了解风险后谨慎参与。"
        type="error"
        icon={<WarningOutlined />}
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 市场概览 */}
      <Card title="期货市场概览" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="合约总数"
              value={marketData.totalContracts}
              prefix={<FundOutlined />}
              suffix="个"
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="上涨合约"
              value={marketData.upContracts}
              prefix={<RiseOutlined style={{ color: '#f5222d' }} />}
              suffix="个"
              valueStyle={{ color: '#f5222d' }}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="下跌合约"
              value={marketData.downContracts}
              prefix={<FallOutlined style={{ color: '#52c41a' }} />}
              suffix="个"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="平盘合约"
              value={marketData.unchangedContracts}
              suffix="个"
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="总成交量"
              value={marketData.totalVolume}
              prefix={<ThunderboltOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="总持仓量"
              value={marketData.totalOpenInterest}
              prefix={<FireOutlined />}
            />
          </Col>
        </Row>
      </Card>

      {/* 股指期货 */}
      <Card title="股指期货" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          {majorFutures.map((future) => (
            <Col xs={12} sm={8} md={6} lg={4} key={future.symbol}>
              <Card size="small" hoverable>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: 4 }}>
                    {future.symbol}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: 8 }}>
                    {future.name}
                  </div>
                  <Statistic
                    value={future.price}
                    precision={2}
                    valueStyle={{
                      fontSize: '14px',
                      color: future.change >= 0 ? '#f5222d' : '#52c41a'
                    }}
                  />
                  <div style={{
                    fontSize: '12px',
                    color: future.change >= 0 ? '#f5222d' : '#52c41a',
                    marginTop: 4
                  }}>
                    {future.change >= 0 ? '+' : ''}{future.change.toFixed(2)}%
                  </div>
                  <div style={{ fontSize: '10px', color: '#999', marginTop: 4 }}>
                    成交量: {future.volume}
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* 商品期货 */}
      <Card title="商品期货" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          {commodityFutures.map((future) => (
            <Col xs={12} sm={8} md={6} lg={4} key={future.symbol}>
              <Card size="small" hoverable>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: 4 }}>
                    {future.symbol}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: 4 }}>
                    {future.name}
                  </div>
                  <Tag size="small" color="blue" style={{ marginBottom: 8 }}>
                    {future.category}
                  </Tag>
                  <Statistic
                    value={future.price}
                    precision={0}
                    valueStyle={{
                      fontSize: '14px',
                      color: future.change >= 0 ? '#f5222d' : '#52c41a'
                    }}
                  />
                  <div style={{
                    fontSize: '12px',
                    color: future.change >= 0 ? '#f5222d' : '#52c41a',
                    marginTop: 4
                  }}>
                    {future.change >= 0 ? '+' : ''}{future.change.toFixed(2)}%
                  </div>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* 热门板块 */}
      <Card title="热门板块" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Tag color="red">有色金属 +2.1%</Tag>
          <Tag color="green">黑色金属 -1.3%</Tag>
          <Tag color="blue">农产品 +0.8%</Tag>
          <Tag color="orange">能源化工 +1.5%</Tag>
          <Tag color="purple">贵金属 -0.7%</Tag>
          <Tag color="cyan">股指期货 +1.2%</Tag>
          <Tag color="geekblue">国债期货 +0.3%</Tag>
          <Tag color="magenta">外汇期货 -0.2%</Tag>
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
              合约筛选
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
    <div className="futures-page">
      <Card
        title={
          <Space>
            <FundOutlined />
            <span>期货市场</span>
            <Tag color="processing">Futures</Tag>
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
                合约筛选
              </span>
            }
            key="screener"
          >
            <AssetScreener
              assetType="futures"
              title="期货合约筛选器"
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
              assetType="futures"
              title="期货策略回测"
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default FuturesPage;
