import React, { useState } from 'react';
import { Card, Tabs, Row, Col, Statistic, Space, Tag, Button, Alert, Progress } from 'antd';
import {
  FundProjectionScreenOutlined,
  RiseOutlined,
  FallOutlined,
  BarChartOutlined,
  SearchOutlined,
  LineChartOutlined,
  DashboardOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  FireOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import AssetScreener from '../components/AssetScreener';
import AssetBacktest from '../components/AssetBacktest';

const { TabPane } = Tabs;

const OptionsPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  // 模拟期权市场数据
  const marketData = {
    totalContracts: 1250,
    callContracts: 680,
    putContracts: 570,
    totalVolume: '856万张',
    totalOpenInterest: '1245万张',
    avgImpliedVolatility: 22.5,
    putCallRatio: 0.84,
  };

  // ETF期权数据
  const etfOptions = [
    {
      symbol: '510050',
      name: '50ETF期权',
      underlyingPrice: 2.856,
      change: 1.2,
      volume: '125万张',
      openInterest: '245万张',
      iv: 18.5
    },
    {
      symbol: '510300',
      name: '300ETF期权',
      underlyingPrice: 4.234,
      change: -0.8,
      volume: '89万张',
      openInterest: '178万张',
      iv: 21.2
    },
    {
      symbol: '159919',
      name: '300ETF期权',
      underlyingPrice: 4.567,
      change: 0.5,
      volume: '67万张',
      openInterest: '134万张',
      iv: 19.8
    },
  ];

  // 股票期权数据
  const stockOptions = [
    {
      symbol: '600036',
      name: '招商银行期权',
      underlyingPrice: 35.67,
      change: 2.1,
      volume: '45万张',
      openInterest: '89万张',
      iv: 25.3
    },
    {
      symbol: '000858',
      name: '五粮液期权',
      underlyingPrice: 156.78,
      change: -1.5,
      volume: '32万张',
      openInterest: '67万张',
      iv: 28.7
    },
  ];

  // 渲染仪表板
  const renderDashboard = () => (
    <div>
      {/* 风险提示 */}
      <Alert
        message="期权交易风险提示"
        description="期权交易具有复杂性和高风险性，可能导致权利金全部损失，请充分了解期权知识和风险后谨慎参与。"
        type="error"
        icon={<WarningOutlined />}
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 市场概览 */}
      <Card title="期权市场概览" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="合约总数"
              value={marketData.totalContracts}
              prefix={<FundProjectionScreenOutlined />}
              suffix="个"
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="看涨期权"
              value={marketData.callContracts}
              prefix={<RiseOutlined style={{ color: '#f5222d' }} />}
              suffix="个"
              valueStyle={{ color: '#f5222d' }}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="看跌期权"
              value={marketData.putContracts}
              prefix={<FallOutlined style={{ color: '#52c41a' }} />}
              suffix="个"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Statistic
              title="PCR比率"
              value={marketData.putCallRatio}
              precision={2}
              valueStyle={{
                color: marketData.putCallRatio > 1 ? '#52c41a' : '#f5222d'
              }}
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

      {/* 隐含波动率指标 */}
      <Card title="隐含波动率指标" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ marginBottom: 8 }}>平均隐含波动率</div>
              <Progress
                type="circle"
                percent={marketData.avgImpliedVolatility}
                format={percent => `${percent}%`}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
            </div>
          </Col>
          <Col xs={24} sm={12}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <span>低波动率 (0-15%): </span>
                <Tag color="green">市场平静</Tag>
              </div>
              <div>
                <span>中等波动率 (15-25%): </span>
                <Tag color="blue">正常波动</Tag>
              </div>
              <div>
                <span>高波动率 (25%+): </span>
                <Tag color="red">市场恐慌</Tag>
              </div>
              <div>
                <span>当前状态: </span>
                <Tag color="blue">正常波动</Tag>
              </div>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* ETF期权 */}
      <Card title="ETF期权" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          {etfOptions.map((option) => (
            <Col xs={24} sm={12} md={8} key={option.symbol}>
              <Card size="small" hoverable>
                <div>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: 8 }}>
                    {option.name}
                  </div>
                  <Row gutter={[8, 8]}>
                    <Col span={12}>
                      <div style={{ fontSize: '12px', color: '#666' }}>标的价格</div>
                      <div style={{
                        fontSize: '14px',
                        fontWeight: 'bold',
                        color: option.change >= 0 ? '#f5222d' : '#52c41a'
                      }}>
                        ¥{option.underlyingPrice}
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ fontSize: '12px', color: '#666' }}>涨跌幅</div>
                      <div style={{
                        fontSize: '14px',
                        fontWeight: 'bold',
                        color: option.change >= 0 ? '#f5222d' : '#52c41a'
                      }}>
                        {option.change >= 0 ? '+' : ''}{option.change.toFixed(2)}%
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ fontSize: '12px', color: '#666' }}>成交量</div>
                      <div style={{ fontSize: '12px' }}>{option.volume}</div>
                    </Col>
                    <Col span={12}>
                      <div style={{ fontSize: '12px', color: '#666' }}>隐含波动率</div>
                      <div style={{ fontSize: '12px' }}>{option.iv}%</div>
                    </Col>
                  </Row>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* 股票期权 */}
      <Card title="股票期权" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          {stockOptions.map((option) => (
            <Col xs={24} sm={12} md={8} key={option.symbol}>
              <Card size="small" hoverable>
                <div>
                  <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: 8 }}>
                    {option.name}
                  </div>
                  <Row gutter={[8, 8]}>
                    <Col span={12}>
                      <div style={{ fontSize: '12px', color: '#666' }}>标的价格</div>
                      <div style={{
                        fontSize: '14px',
                        fontWeight: 'bold',
                        color: option.change >= 0 ? '#f5222d' : '#52c41a'
                      }}>
                        ¥{option.underlyingPrice}
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ fontSize: '12px', color: '#666' }}>涨跌幅</div>
                      <div style={{
                        fontSize: '14px',
                        fontWeight: 'bold',
                        color: option.change >= 0 ? '#f5222d' : '#52c41a'
                      }}>
                        {option.change >= 0 ? '+' : ''}{option.change.toFixed(2)}%
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ fontSize: '12px', color: '#666' }}>成交量</div>
                      <div style={{ fontSize: '12px' }}>{option.volume}</div>
                    </Col>
                    <Col span={12}>
                      <div style={{ fontSize: '12px', color: '#666' }}>隐含波动率</div>
                      <div style={{ fontSize: '12px' }}>{option.iv}%</div>
                    </Col>
                  </Row>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>

      {/* 期权策略 */}
      <Card title="常用期权策略" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={8} md={6}>
            <Card size="small" hoverable style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: 4 }}>
                买入看涨
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                看涨标的价格
              </div>
              <Tag color="red" style={{ marginTop: 8 }}>牛市策略</Tag>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small" hoverable style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: 4 }}>
                买入看跌
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                看跌标的价格
              </div>
              <Tag color="green" style={{ marginTop: 8 }}>熊市策略</Tag>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small" hoverable style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: 4 }}>
                跨式组合
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                预期大幅波动
              </div>
              <Tag color="blue" style={{ marginTop: 8 }}>波动策略</Tag>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <Card size="small" hoverable style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: 4 }}>
                备兑开仓
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                持股卖出看涨
              </div>
              <Tag color="orange" style={{ marginTop: 8 }}>收益增强</Tag>
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
              期权筛选
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
              期权计算器
            </Button>
          </Col>
        </Row>
      </Card>
    </div>
  );

  return (
    <div className="options-page">
      <Card
        title={
          <Space>
            <FundProjectionScreenOutlined />
            <span>期权市场</span>
            <Tag color="processing">Options</Tag>
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
                期权筛选
              </span>
            }
            key="screener"
          >
            <AssetScreener
              assetType="options"
              title="期权合约筛选器"
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
              assetType="options"
              title="期权策略回测"
            />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default OptionsPage;
