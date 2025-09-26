import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Card,
  Row,
  Col,
  Typography
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getAllStrategies,
  createStrategy,
  updateStrategy,
  deleteStrategy,
  getAllBacktestResults,
  runBacktest,
  executeStrategy
} from '../api/strategyApi';

const { Title } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const StrategyManagementPage = () => {
  const [strategies, setStrategies] = useState([]);
  const [backtestResults, setBacktestResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadStrategies();
    loadBacktestResults();
  }, []);

  const loadStrategies = async () => {
    setLoading(true);
    try {
      const response = await getAllStrategies();
      setStrategies(response.data);
    } catch (error) {
      message.error('加载策略失败');
    } finally {
      setLoading(false);
    }
  };

  const loadBacktestResults = async () => {
    try {
      const response = await getAllBacktestResults();
      setBacktestResults(response.data);
    } catch (error) {
      message.error('加载回测结果失败');
    }
  };

  const handleCreateStrategy = async (values) => {
    try {
      if (editingStrategy) {
        await updateStrategy(editingStrategy.id, values);
        message.success('策略更新成功');
      } else {
        await createStrategy(values);
        message.success('策略创建成功');
      }
      setModalVisible(false);
      setEditingStrategy(null);
      form.resetFields();
      loadStrategies();
    } catch (error) {
      message.error(editingStrategy ? '更新策略失败' : '创建策略失败');
    }
  };

  const handleDeleteStrategy = async (id) => {
    try {
      await deleteStrategy(id);
      message.success('策略删除成功');
      loadStrategies();
    } catch (error) {
      message.error('删除策略失败');
    }
  };

  const handleRunBacktest = async (strategyId) => {
    try {
      const strategy = strategies.find(s => s.id === strategyId);
      const backtestConfig = {
        strategy_id: strategyId,
        symbol: strategy.definition.symbols[0],
        interval: strategy.definition.interval,
        start_date: dayjs().subtract(1, 'year').format('YYYY-MM-DD'),
        end_date: dayjs().format('YYYY-MM-DD'),
        initial_capital: 100000
      };

      await runBacktest(backtestConfig);
      message.success('回测执行成功');
      loadBacktestResults();
    } catch (error) {
      message.error('执行回测失败');
    }
  };

  const handleExecuteStrategy = async (strategyId) => {
    try {
      const strategy = strategies.find(s => s.id === strategyId);
      await executeStrategy(strategyId, strategy.definition.symbols[0]);
      message.success('策略执行成功');
    } catch (error) {
      message.error('执行策略失败');
    }
  };

  const strategyColumns = [
    {
      title: '策略名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text) => text || '暂无描述',
    },
    {
      title: '标的',
      dataIndex: 'definition',
      key: 'symbols',
      render: (definition) => definition.symbols.join(', '),
    },
    {
      title: '间隔',
      dataIndex: 'definition',
      key: 'interval',
      render: (definition) => definition.interval,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="primary"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleExecuteStrategy(record.id)}
          >
            执行
          </Button>
          <Button
            size="small"
            onClick={() => handleRunBacktest(record.id)}
          >
            回测
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingStrategy(record);
              setModalVisible(true);
              form.setFieldsValue(record);
            }}
          >
            编辑
          </Button>
          <Button
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteStrategy(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const backtestColumns = [
    {
      title: '策略',
      dataIndex: 'strategy_id',
      key: 'strategy',
      render: (strategyId) => {
        const strategy = strategies.find(s => s.id === strategyId);
        return strategy ? strategy.name : '未知策略';
      },
    },
    {
      title: '标的',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '总收益',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: '年化收益',
      dataIndex: 'annual_return',
      key: 'annual_return',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: '夏普比率',
      dataIndex: 'sharpe_ratio',
      key: 'sharpe_ratio',
      render: (value) => value.toFixed(2),
    },
    {
      title: '最大回撤',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: '胜率',
      dataIndex: 'win_rate',
      key: 'win_rate',
      render: (value) => `${(value * 100).toFixed(2)}%`,
    },
    {
      title: '回测时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card
            title={
              <Space>
                <Title level={4} style={{ margin: 0 }}>策略管理</Title>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setModalVisible(true)}
                >
                  创建策略
                </Button>
              </Space>
            }
          >
            <Table
              columns={strategyColumns}
              dataSource={strategies}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>

        <Col span={24}>
          <Card
            title={
              <Space>
                <Title level={4} style={{ margin: 0 }}>回测结果</Title>
                <Button
                  icon={<HistoryOutlined />}
                  onClick={loadBacktestResults}
                >
                  刷新
                </Button>
              </Space>
            }
          >
            <Table
              columns={backtestColumns}
              dataSource={backtestResults}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
      </Row>

      <Modal
        title={editingStrategy ? '编辑策略' : '创建策略'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingStrategy(null);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateStrategy}
          initialValues={{
            interval: 'daily',
            symbols: ['000001.SZ']
          }}
        >
          <Form.Item
            name="name"
            label="策略名称"
            rules={[{ required: true, message: '请输入策略名称' }]}
          >
            <Input placeholder="请输入策略名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="策略描述"
          >
            <TextArea rows={3} placeholder="请输入策略描述" />
          </Form.Item>

          <Form.Item
            name={['definition', 'symbols']}
            label="交易标的"
            rules={[{ required: true, message: '请选择交易标的' }]}
          >
            <Select
              mode="tags"
              placeholder="请输入股票代码，如 000001.SZ"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name={['definition', 'interval']}
            label="时间间隔"
            rules={[{ required: true, message: '请选择时间间隔' }]}
          >
            <Select placeholder="请选择时间间隔">
              <Option value="daily">日线</Option>
              <Option value="weekly">周线</Option>
              <Option value="monthly">月线</Option>
              <Option value="60min">60分钟</Option>
              <Option value="30min">30分钟</Option>
              <Option value="15min">15分钟</Option>
              <Option value="5min">5分钟</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name={['definition', 'conditions']}
            label="交易条件"
            rules={[{ required: true, message: '请输入交易条件' }]}
          >
            <TextArea
              rows={4}
              placeholder={`请输入交易条件，例如：
{
  "buy": [
    {
      "type": "technical",
      "indicator": "rsi",
      "operator": "<",
      "value": 30
    }
  ],
  "sell": [
    {
      "type": "technical",
      "indicator": "rsi",
      "operator": ">",
      "value": 70
    }
  ]
}`}
            />
          </Form.Item>

          <Form.Item
            name={['definition', 'actions']}
            label="交易动作"
            rules={[{ required: true, message: '请输入交易动作' }]}
          >
            <TextArea
              rows={3}
              placeholder={`请输入交易动作，例如：
{
  "buy": {
    "type": "market",
    "amount": 1000
  },
  "sell": {
    "type": "market",
    "percentage": 0.5
  }
}`}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingStrategy ? '更新策略' : '创建策略'}
              </Button>
              <Button onClick={() => {
                setModalVisible(false);
                setEditingStrategy(null);
                form.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default StrategyManagementPage;
