import React, { useState } from 'react';
import { Card, Tabs, Row, Col, Statistic, Space, Tag, Button, Alert } from 'antd';
import {
  BitcoinOutlined,
  RiseOutlined,
  FallOutlined,
  BarChartOutlined,
  SearchOutlined,
  LineChartOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import AssetScreener from '../components/AssetScreener';
import AssetBacktest from '../components/AssetBacktest';

const { TabPane } = Tabs;

const CryptoPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  // 模拟加密货币市场数据
  const marketData = {
    totalCoins: 12500,
    upCoins: 6200,
    downCoins: 5100,
    unchangedCoins: 1200,
    totalMarketCap: '$2.1T',
    btcDominance: 42.5,
    fearGreedIndex: 65,
    volume24h: '$89.5B',
  };

  // 主要加密货币数据
  const majorCryptos = [
    { symbol: 'BTC', name: 'Bitcoin', price: 43250.67, change: 2.8, marketCap: '$845B' },
    { symbol: 'ETH', name: 'Ethereum', price: 2567.89, change: -1.2, marketCap: '$308B' },
    { symbol: 'BNB', name: 'BNB', price: 345.12, change: 1.5, marketCap: '$53B' },
    { symbol: 'SOL', name: 'Solana', price: 98.76, change: 4.2, marketCap: '$42B' },
    { symbol: 'ADA', name: 'Cardano', price: 0.52, change: -0.8, marketCap: '$18B' },
    { symbol: 'AVAX', name: 'Avalanche', price: 36.45, change: 3.1, marketCap: '$13B' },
  ];

  // 渲染仪表板
  const renderDashboard = () => (
    <div>
      {/* 风险提示 */}
      <Alert
        message="风险提示"
        description="加密货币投资具有极高风险，价格波动剧烈，请谨慎投资，理性决策。"
        type="warning"
        icon={<WarningOutlined />}
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 市场指标 */}
      <Card title="市场指标" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="总市值"
              value={marketData.totalMarketCap}
              prefix={<BitcoinOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="24h交易量"
              value={marketData.volume24h}
              prefix={<ThunderboltOutlined />}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="BTC市值占比"
              value={marketData.btcDominance}
              precision={1}
              suffix="%"
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="恐慌贪婪指数"
              value={marketData.fearGreedIndex}
              suffix="/100"
              valueStyle={{ 
                color: marketData.fearGreedIndex > 50 ? '#f5222d' : '#52c41a' 
              }}
            />
          </Col>
        </Row>
      </Card>

      {/* 市场概览 */}
      <Card title="市场概览" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="总币种数"
              value={marketData.totalCoins}
              suffix="种"
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="上涨币种"
              value={marketData.upCoins}
              prefix={<RiseOutlined style={{ color: '#f5222d' }} />}
              suffix="种"
              valueStyle={{ color: '#f5222d' }}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="下跌币种"
              value={marketData.downCoins}
              prefix={<FallOutlined style={{ color: '#52c41a' }} />}
              suffix="种"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="平盘币种"
              value={marketData.unchangedCoins}
              suffix="种"
            />
          </Col>
        </Row>
      </Card>

      {/* 主要加密货币 */}
      <Card title="主要加密货币" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          {majorCryptos.map((crypto) => (
            <Col xs={12} sm={8} md={6} lg={4} key={crypto.symbol}>
              <Card size="small" hoverable>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: 4 }}>
                    {crypto.symbol}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: 8 }}>
                    {crypto.name}
                  </div>
                  <Statistic
                    value={crypto.price}
                    precision={crypto.symbol === 'BTC' ? 2 : crypto.price < 1 ? 4 : 2}
                    prefix="$"
                    valueStyle={{ 
                      fontSize: '14px',
                      color: crypto.change >= 0 ? '#f5222d' : '#52c41a'
                    }}
                  />
                  <div style={{ 
                    fontSize: '12px', 
                    color: crypto.change >= 0 ? '#f5222d' : '#52c41a',
                    marginTop: 4
                  }}>
                    {crypto.change >= 0 ? '+' : ''}{crypto.change.toFixed(2)}%
                  </div>
                  <div style={{ fontSize: '10px', color: '#999', marginTop: 4 }}>
                    市值: {crypto.marketCap}
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
          <Tag color="red">DeFi +5.2%</Tag>
          <Tag color="green">NFT -3.1%</Tag>
          <Tag color="blue">Layer1 +2.8%</Tag>
          <Tag color="orange">GameFi +4.5%</Tag>
          <Tag color="purple">Metaverse -1.2%</Tag>
          <Tag color="cyan">Web3 +1.9%</Tag>
          <Tag color="geekblue">AI +6.3%</Tag>
          <Tag color="magenta">Meme -2.8%</Tag>
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
              币种筛选
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
    <div className="crypto-page">
      <Card
        title={
          <Space>
            <BitcoinOutlined />
            <span>加密货币</span>
            <Tag color="processing">Crypto</Tag>
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
                币种筛选
              </span>
            }
            key="screener"
          >
            <AssetScreener
              assetType="crypto"
              title="加密货币筛选器"
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
              assetType="crypto"
              title="加密货币回测"
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default CryptoPage;