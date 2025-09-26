import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Typography,
  Button,
  Spin,
  Alert,
  Space,
  Progress
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  DollarOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { getBacktestResultById } from '../api/strategyApi';
import BacktestChart from '../components/BacktestChart';

const { Title, Text } = Typography;

const BacktestResultPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const response = await getBacktestResultById(id);
        setResult(response.data);
      } catch (error) {
        setError('加载回测结果失败');
      } finally {
        setLoading(false);
      }
    };
    fetchResult();
  }, [id]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="错误"
        description={error}
        type="error"
        showIcon
        style={{ margin: '24px' }}
      />
    );
  }

  if (!result) {
    return (
      <Alert
        message="未找到回测结果"
        type="warning"
        showIcon
        style={{ margin: '24px' }}
      />
    );
  }

  const performanceStats = [
    {
      title: '总收益率',
      value: result.total_return * 100,
      precision: 2,
      suffix: '%',
      valueStyle: { color: result.total_return >= 0 ? '#3f8600' : '#cf1322' },
      prefix: result.total_return >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />
    },
    {
      title: '年化收益率',
      value: result.annual_return * 100,
      precision: 2,
      suffix: '%',
      valueStyle: { color: result.annual_return >= 0 ? '#3f8600' : '#cf1322' },
      prefix: result.annual_return >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />
    },
    {
      title: '夏普比率',
      value: result.sharpe_ratio,
      precision: 2,
      valueStyle: { color: result.sharpe_ratio >= 1 ? '#3f8600' : result.sharpe_ratio >= 0 ? '#faad14' : '#cf1322' }
    },
    {
      title: '最大回撤',
      value: result.max_drawdown * 100,
      precision: 2,
      suffix: '%',
      valueStyle: { color: result.max_drawdown <= 0.2 ? '#3f8600' : result.max_drawdown <= 0.4 ? '#faad14' : '#cf1322' }
    },
    {
      title: '胜率',
      value: result.win_rate * 100,
      precision: 2,
      suffix: '%',
      valueStyle: { color: result.win_rate >= 0.6 ? '#3f8600' : result.win_rate >= 0.4 ? '#faad14' : '#cf1322' }
    },
    {
      title: '初始资金',
      value: result.initial_capital,
      precision: 2,
      prefix: '¥',
      valueStyle: { color: '#1890ff' }
    }
  ];

  const transactionColumns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => (
        <Tag color={type === 'buy' ? 'green' : 'red'}>
          {type === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      render: (price) => `¥${price.toFixed(2)}`,
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount) => `¥${amount.toFixed(2)}`,
    },
    {
      title: '手续费',
      dataIndex: 'commission',
      key: 'commission',
      render: (commission) => `¥${commission.toFixed(2)}`,
    },
    {
      title: '持仓',
      dataIndex: 'position',
      key: 'position',
    },
    {
      title: '现金',
      dataIndex: 'cash',
      key: 'cash',
      render: (cash) => `¥${cash.toFixed(2)}`,
    },
    {
      title: '总资产',
      dataIndex: 'total_assets',
      key: 'total_assets',
      render: (assets) => `¥${assets.toFixed(2)}`,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 头部信息 */}
        <Card>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Title level={2}>
              <BarChartOutlined /> 回测结果详情
            </Title>
            <Text type="secondary">
              策略: {result.strategy_name} | 标的: {result.symbol} |
              周期: {result.start_date} 至 {result.end_date}
            </Text>
          </Space>
        </Card>

        {/* 性能指标 */}
        <Card title="性能指标" extra={<LineChartOutlined />}>
          <Row gutter={[16, 16]}>
            {performanceStats.map((stat, index) => (
              <Col xs={24} sm={12} md={8} lg={6} key={index}>
                <Card size="small">
                  <Statistic
                    title={stat.title}
                    value={stat.value}
                    precision={stat.precision}
                    valueStyle={stat.valueStyle}
                    prefix={stat.prefix}
                    suffix={stat.suffix}
                  />
                </Card>
              </Col>
            ))}
          </Row>
        </Card>

        {/* 资金曲线图 */}
        <Card title="资金曲线" extra={<LineChartOutlined />}>
          {result.chart_data && (
            <BacktestChart data={result.chart_data} />
          )}
        </Card>

        {/* 交易明细 */}
        <Card
          title={`交易记录 (共 ${result.transactions?.length || 0} 笔)`}
          extra={
            <Button icon={<DownloadOutlined />} size="small">
              导出CSV
            </Button>
          }
        >
          {result.transactions && result.transactions.length > 0 ? (
            <Table
              columns={transactionColumns}
              dataSource={result.transactions}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              scroll={{ x: 1000 }}
              size="small"
            />
          ) : (
            <Alert
              message="暂无交易记录"
              type="info"
              showIcon
            />
          )}
        </Card>

        {/* 持仓分析 */}
        <Card title="持仓分析" extra={<PieChartOutlined />}>
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card size="small" title="持仓统计">
                <Space direction="vertical">
                  <Text>最大持仓: {result.max_position || 0}</Text>
                  <Text>平均持仓: {result.avg_position || 0}</Text>
                  <Text>持仓天数: {result.holding_days || 0}</Text>
                </Space>
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small" title="交易频率">
                <Space direction="vertical">
                  <Text>交易次数: {result.transaction_count || 0}</Text>
                  <Text>买入次数: {result.buy_count || 0}</Text>
                  <Text>卖出次数: {result.sell_count || 0}</Text>
                  <Progress
                    percent={result.buy_count && result.transaction_count
                      ? Math.round((result.buy_count / result.transaction_count) * 100)
                      : 0
                    }
                    format={(percent) => `买入占比: ${percent}%`}
                  />
                </Space>
              </Card>
            </Col>
          </Row>
        </Card>

        {/* 风险分析 */}
        <Card title="风险分析" extra={<DollarOutlined />}>
          <Row gutter={[16, 16]}>
            <Col span={8}>
              <Card size="small" title="波动率">
                <Statistic
                  title="年化波动率"
                  value={result.volatility ? result.volatility * 100 : 0}
                  precision={2}
                  suffix="%"
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="回撤分析">
                <Space direction="vertical">
                  <Text>最大回撤期: {result.max_drawdown_period || 0}天</Text>
                  <Text>恢复期: {result.recovery_period || 0}天</Text>
                </Space>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="盈亏分布">
                <Space direction="vertical">
                  <Text>平均盈利: ¥{result.avg_profit?.toFixed(2) || 0}</Text>
                  <Text>平均亏损: ¥{result.avg_loss?.toFixed(2) || 0}</Text>
                  <Text>盈亏比: {result.profit_loss_ratio?.toFixed(2) || 0}</Text>
                </Space>
              </Card>
            </Col>
          </Row>
        </Card>

        {/* 操作按钮 */}
        <Card>
          <Space>
            <Button
              type="primary"
              onClick={() => navigate('/strategies')}
            >
              返回策略列表
            </Button>
            <Button
              onClick={() => navigate(`/backtest/run?strategy_id=${result.strategy_id}`)}
            >
              再次回测
            </Button>
            <Button icon={<DownloadOutlined />}>
              导出报告
            </Button>
          </Space>
        </Card>
      </Space>
    </div>
  );
};

export default BacktestResultPage;
