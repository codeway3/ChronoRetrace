import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Row,
  Col,
  InputNumber,
  Select,
  Button,
  DatePicker,
  message,
  Spin,
  Space,
  Tag,
  Tooltip,
  Tabs,
  Table,
  Progress,
} from 'antd';
import {
  PlayCircleOutlined,
  ReloadOutlined,
  DownloadOutlined,
  InfoCircleOutlined,
  SettingOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { Line } from '@ant-design/plots';
import { assetBacktestApi } from '../api/assetApi';
import dayjs from 'dayjs';

const { Option } = Select;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

const AssetBacktest = ({ assetType, title }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [strategiesLoading, setStrategiesLoading] = useState(true);
  const [backtestResult, setBacktestResult] = useState(null);
  const [supportedStrategies, setSupportedStrategies] = useState([]);
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [activeTab, setActiveTab] = useState('config');

  // 获取支持的策略列表
  useEffect(() => {
    const fetchSupportedStrategies = async () => {
      if (!assetType) return;
      
      try {
        setStrategiesLoading(true);
        const response = await assetBacktestApi.getSupportedStrategies(assetType);
        setSupportedStrategies(response.data.strategies || []);
      } catch (error) {
        console.error('获取支持的策略列表失败:', error);
        message.error('获取支持的策略列表失败');
      } finally {
        setStrategiesLoading(false);
      }
    };

    fetchSupportedStrategies();
  }, [assetType]);

  // 执行回溯测试
  const handleBacktest = async (values) => {
    if (!assetType) {
      message.warning('请选择资产类型');
      return;
    }

    try {
      setLoading(true);
      const config = {
        ...values,
        start_date: values.date_range[0].format('YYYY-MM-DD'),
        end_date: values.date_range[1].format('YYYY-MM-DD'),
      };
      delete config.date_range;

      const response = await assetBacktestApi.backtestGridStrategy(assetType, config);
      setBacktestResult(response.data);
      setActiveTab('results');
      message.success('回溯测试完成');
    } catch (error) {
      console.error('回溯测试失败:', error);
      message.error('回溯测试失败，请检查配置参数');
    } finally {
      setLoading(false);
    }
  };

  // 执行策略优化
  const handleOptimize = async (values) => {
    if (!assetType) {
      message.warning('请选择资产类型');
      return;
    }

    try {
      setLoading(true);
      const config = {
        ...values,
        start_date: values.date_range[0].format('YYYY-MM-DD'),
        end_date: values.date_range[1].format('YYYY-MM-DD'),
      };
      delete config.date_range;

      const response = await assetBacktestApi.optimizeGridStrategy(assetType, config);
      setOptimizationResult(response.data);
      setActiveTab('optimization');
      message.success('策略优化完成');
    } catch (error) {
      console.error('策略优化失败:', error);
      message.error('策略优化失败，请检查配置参数');
    } finally {
      setLoading(false);
    }
  };

  // 重置配置
  const handleReset = () => {
    form.resetFields();
    setBacktestResult(null);
    setOptimizationResult(null);
    setActiveTab('config');
  };

  // 导出结果
  const handleExport = () => {
    if (!backtestResult) {
      message.warning('没有可导出的回测结果');
      return;
    }
    
    // 这里可以实现导出功能
    message.info('导出功能开发中...');
  };

  // 渲染配置表单
  const renderConfigForm = () => (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleBacktest}
      initialValues={{
        date_range: [dayjs().subtract(1, 'year'), dayjs()],
        initial_capital: 100000,
        grid_count: 10,
        price_range: 0.2,
        strategy: 'grid',
      }}
    >
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <Form.Item
            label="回测时间范围"
            name="date_range"
            rules={[{ required: true, message: '请选择回测时间范围' }]}
          >
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
        </Col>
        
        <Col xs={24} sm={12} md={8}>
          <Form.Item
            label="标的代码"
            name="symbol"
            rules={[{ required: true, message: '请输入标的代码' }]}
          >
            <Select
              placeholder="请输入或选择标的代码"
              showSearch
              allowClear
              filterOption={(input, option) =>
                option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
              }
            >
              {/* 这里可以根据资产类型动态加载标的列表 */}
              <Option value="000001">000001 - 平安银行</Option>
              <Option value="000002">000002 - 万科A</Option>
            </Select>
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Form.Item
            label="策略类型"
            name="strategy"
            rules={[{ required: true, message: '请选择策略类型' }]}
          >
            <Select placeholder="请选择策略类型">
              {supportedStrategies.map((strategy) => (
                <Option key={strategy.code} value={strategy.code}>
                  {strategy.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Form.Item
            label={
              <Space>
                初始资金
                <Tooltip title="回测的初始投资金额">
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              </Space>
            }
            name="initial_capital"
            rules={[{ required: true, message: '请输入初始资金' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1000}
              max={10000000}
              step={1000}
              formatter={value => `¥ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value.replace(/¥\s?|(,*)/g, '')}
            />
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Form.Item
            label={
              <Space>
                网格数量
                <Tooltip title="网格策略的网格数量，影响交易频率">
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              </Space>
            }
            name="grid_count"
            rules={[{ required: true, message: '请输入网格数量' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={5}
              max={50}
              step={1}
            />
          </Form.Item>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Form.Item
            label={
              <Space>
                价格波动范围
                <Tooltip title="网格策略覆盖的价格波动范围（比例）">
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                </Tooltip>
              </Space>
            }
            name="price_range"
            rules={[{ required: true, message: '请输入价格波动范围' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0.1}
              max={1.0}
              step={0.05}
              formatter={value => `${(value * 100).toFixed(0)}%`}
              parser={value => value.replace('%', '') / 100}
            />
          </Form.Item>
        </Col>
      </Row>
      
      <Row justify="center" style={{ marginTop: 24 }}>
        <Space size="middle">
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            htmlType="submit"
            loading={loading}
            size="large"
          >
            开始回测
          </Button>
          <Button
            icon={<SettingOutlined />}
            onClick={() => form.submit()}
            loading={loading}
            size="large"
          >
            策略优化
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleReset}
            size="large"
          >
            重置配置
          </Button>
        </Space>
      </Row>
    </Form>
  );

  // 渲染回测结果
  const renderBacktestResults = () => {
    if (!backtestResult) return <div>暂无回测结果</div>;

    const { performance, trades, equity_curve } = backtestResult;

    // 收益曲线图配置
    const equityConfig = {
      data: equity_curve || [],
      xField: 'date',
      yField: 'equity',
      smooth: true,
      color: '#1890ff',
      point: {
        size: 2,
        shape: 'circle',
      },
      tooltip: {
        formatter: (datum) => ({
          name: '账户净值',
          value: `¥${datum.equity?.toFixed(2)}`,
        }),
      },
    };

    // 交易记录表格列
    const tradeColumns = [
      {
        title: '时间',
        dataIndex: 'timestamp',
        key: 'timestamp',
        render: (value) => dayjs(value).format('YYYY-MM-DD HH:mm'),
      },
      {
        title: '类型',
        dataIndex: 'type',
        key: 'type',
        render: (value) => (
          <Tag color={value === 'buy' ? 'green' : 'red'}>
            {value === 'buy' ? '买入' : '卖出'}
          </Tag>
        ),
      },
      {
        title: '价格',
        dataIndex: 'price',
        key: 'price',
        render: (value) => `¥${value?.toFixed(2)}`,
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
        render: (value) => `¥${value?.toFixed(2)}`,
      },
    ];

    return (
      <div>
        {/* 性能指标 */}
        <Card title="回测性能" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={8} md={6}>
              <div className="performance-metric">
                <div className="metric-label">总收益率</div>
                <div className="metric-value" style={{ 
                  color: performance?.total_return >= 0 ? '#f5222d' : '#52c41a' 
                }}>
                  {performance?.total_return?.toFixed(2)}%
                </div>
              </div>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <div className="performance-metric">
                <div className="metric-label">年化收益率</div>
                <div className="metric-value">
                  {performance?.annual_return?.toFixed(2)}%
                </div>
              </div>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <div className="performance-metric">
                <div className="metric-label">最大回撤</div>
                <div className="metric-value" style={{ color: '#f5222d' }}>
                  {performance?.max_drawdown?.toFixed(2)}%
                </div>
              </div>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <div className="performance-metric">
                <div className="metric-label">夏普比率</div>
                <div className="metric-value">
                  {performance?.sharpe_ratio?.toFixed(2)}
                </div>
              </div>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <div className="performance-metric">
                <div className="metric-label">交易次数</div>
                <div className="metric-value">
                  {trades?.length || 0}
                </div>
              </div>
            </Col>
            <Col xs={12} sm={8} md={6}>
              <div className="performance-metric">
                <div className="metric-label">胜率</div>
                <div className="metric-value">
                  {performance?.win_rate?.toFixed(2)}%
                </div>
              </div>
            </Col>
          </Row>
        </Card>

        {/* 收益曲线 */}
        <Card title="收益曲线" style={{ marginBottom: 16 }}>
          <Line {...equityConfig} height={300} />
        </Card>

        {/* 交易记录 */}
        <Card title="交易记录">
          <Table
            columns={tradeColumns}
            dataSource={trades}
            rowKey={(record, index) => index}
            pagination={{ pageSize: 10 }}
            size="small"
          />
        </Card>
      </div>
    );
  };

  // 渲染优化结果
  const renderOptimizationResults = () => {
    if (!optimizationResult) return <div>暂无优化结果</div>;

    return (
      <Card title="策略优化结果">
        <div>优化功能开发中...</div>
      </Card>
    );
  };

  return (
    <div className="asset-backtest">
      <Card
        title={
          <Space>
            <span>{title || `${assetType?.toUpperCase()} 回溯测试`}</span>
            {assetType && <Tag color="processing">{assetType}</Tag>}
          </Space>
        }
        loading={strategiesLoading}
        extra={
          <Space>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExport}
              disabled={!backtestResult}
            >
              导出结果
            </Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab="策略配置" key="config" icon={<SettingOutlined />}>
            {renderConfigForm()}
          </TabPane>
          
          <TabPane tab="回测结果" key="results" icon={<BarChartOutlined />}>
            {renderBacktestResults()}
          </TabPane>
          
          <TabPane tab="策略优化" key="optimization" icon={<SettingOutlined />}>
            {renderOptimizationResults()}
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default AssetBacktest;