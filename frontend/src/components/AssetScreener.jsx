import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Row,
  Col,
  InputNumber,
  Select,
  Button,
  Table,
  message,
  Space,
  Tag,
  Tooltip,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  DownloadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { assetScreenerApi } from '../api/assetApi';

const { Option } = Select;

const AssetScreener = ({ assetType, title }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [criteriaLoading, setCriteriaLoading] = useState(true);
  const [results, setResults] = useState([]);
  const [criteriaConfig, setCriteriaConfig] = useState(null);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 50,
    total: 0,
  });

  // 获取筛选条件配置
  useEffect(() => {
    const fetchCriteriaConfig = async () => {
      if (!assetType) return;

      try {
        setCriteriaLoading(true);
        const response = await assetScreenerApi.getCriteriaConfig(assetType);
        setCriteriaConfig(response.data.criteria);
      } catch (error) {
        console.error('获取筛选条件配置失败:', error);
        message.error('获取筛选条件配置失败');
      } finally {
        setCriteriaLoading(false);
      }
    };

    fetchCriteriaConfig();
  }, [assetType]);

  // 执行筛选
  const handleScreen = async (values) => {
    if (!assetType) {
      message.warning('请选择资产类型');
      return;
    }

    try {
      setLoading(true);
      const response = await assetScreenerApi.screenStocks(assetType, {
        criteria: values,
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
      });

      setResults(response.data.stocks || []);
      setPagination(prev => ({
        ...prev,
        total: response.data.total || 0,
      }));

      message.success(`筛选完成，找到 ${response.data.total || 0} 只符合条件的标的`);
    } catch (error) {
      console.error('筛选失败:', error);
      message.error('筛选失败，请检查筛选条件');
    } finally {
      setLoading(false);
    }
  };

  // 重置筛选条件
  const handleReset = () => {
    form.resetFields();
    setResults([]);
    setPagination(prev => ({
      ...prev,
      current: 1,
      total: 0,
    }));
  };

  // 导出结果
  const handleExport = () => {
    if (results.length === 0) {
      message.warning('没有可导出的数据');
      return;
    }

    // 这里可以实现导出功能
    message.info('导出功能开发中...');
  };

  // 表格分页处理
  const handleTableChange = (newPagination) => {
    setPagination(newPagination);
    // 重新执行筛选
    form.submit();
  };

  // 渲染筛选条件表单
  const renderCriteriaForm = () => {
    if (!criteriaConfig) return null;

    return (
      <Form
        form={form}
        layout="vertical"
        onFinish={handleScreen}
      >
        <Row gutter={[16, 16]}>
          {criteriaConfig.map((criterion) => (
            <Col xs={24} sm={12} md={8} lg={6} key={criterion.key}>
              <Form.Item
                label={
                  <Space>
                    {criterion.label}
                    {criterion.description && (
                      <Tooltip title={criterion.description}>
                        <InfoCircleOutlined style={{ color: '#1890ff' }} />
                      </Tooltip>
                    )}
                  </Space>
                }
                name={criterion.key}
              >
                {criterion.type === 'number' && (
                  <InputNumber
                    style={{ width: '100%' }}
                    min={criterion.min}
                    max={criterion.max}
                    step={criterion.step || 0.01}
                    placeholder={criterion.placeholder}
                  />
                )}
                {criterion.type === 'range' && (
                  <InputNumber.Group compact>
                    <Form.Item name={[criterion.key, 'min']} noStyle>
                      <InputNumber
                        style={{ width: '50%' }}
                        placeholder="最小值"
                        min={criterion.min}
                        max={criterion.max}
                      />
                    </Form.Item>
                    <Form.Item name={[criterion.key, 'max']} noStyle>
                      <InputNumber
                        style={{ width: '50%' }}
                        placeholder="最大值"
                        min={criterion.min}
                        max={criterion.max}
                      />
                    </Form.Item>
                  </InputNumber.Group>
                )}
                {criterion.type === 'select' && (
                  <Select
                    placeholder={criterion.placeholder}
                    allowClear
                    mode={criterion.multiple ? 'multiple' : undefined}
                  >
                    {criterion.options?.map((option) => (
                      <Option key={option.value} value={option.value}>
                        {option.label}
                      </Option>
                    ))}
                  </Select>
                )}
              </Form.Item>
            </Col>
          ))}
        </Row>

        <Row justify="center" style={{ marginTop: 24 }}>
          <Space size="middle">
            <Button
              type="primary"
              icon={<SearchOutlined />}
              htmlType="submit"
              loading={loading}
              size="large"
            >
              开始筛选
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              size="large"
            >
              重置条件
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExport}
              disabled={results.length === 0}
              size="large"
            >
              导出结果
            </Button>
          </Space>
        </Row>
      </Form>
    );
  };

  // 表格列配置
  const getTableColumns = () => {
    const baseColumns = [
      {
        title: '代码',
        dataIndex: 'symbol',
        key: 'symbol',
        width: 100,
        fixed: 'left',
      },
      {
        title: '名称',
        dataIndex: 'name',
        key: 'name',
        width: 150,
        fixed: 'left',
      },
      {
        title: '当前价格',
        dataIndex: 'current_price',
        key: 'current_price',
        width: 100,
        render: (value) => value ? `¥${value.toFixed(2)}` : '-',
      },
      {
        title: '涨跌幅',
        dataIndex: 'change_percent',
        key: 'change_percent',
        width: 100,
        render: (value) => {
          if (value === null || value === undefined) return '-';
          const color = value >= 0 ? '#f5222d' : '#52c41a';
          return <span style={{ color }}>{value.toFixed(2)}%</span>;
        },
      },
      {
        title: '市值',
        dataIndex: 'market_cap',
        key: 'market_cap',
        width: 120,
        render: (value) => {
          if (!value) return '-';
          if (value >= 1e8) return `${(value / 1e8).toFixed(2)}亿`;
          if (value >= 1e4) return `${(value / 1e4).toFixed(2)}万`;
          return value.toFixed(2);
        },
      },
      {
        title: '成交量',
        dataIndex: 'volume',
        key: 'volume',
        width: 120,
        render: (value) => {
          if (!value) return '-';
          if (value >= 1e8) return `${(value / 1e8).toFixed(2)}亿`;
          if (value >= 1e4) return `${(value / 1e4).toFixed(2)}万`;
          return value.toFixed(0);
        },
      },
    ];

    // 根据资产类型添加特定列
    if (assetType === 'a-share' || assetType === 'us-stock') {
      baseColumns.push(
        {
          title: 'PE比率',
          dataIndex: 'pe_ratio',
          key: 'pe_ratio',
          width: 100,
          render: (value) => value ? value.toFixed(2) : '-',
        },
        {
          title: 'PB比率',
          dataIndex: 'pb_ratio',
          key: 'pb_ratio',
          width: 100,
          render: (value) => value ? value.toFixed(2) : '-',
        }
      );
    }

    if (assetType === 'a-share') {
      baseColumns.push({
        title: '行业',
        dataIndex: 'industry',
        key: 'industry',
        width: 120,
        render: (value) => value ? <Tag color="blue">{value}</Tag> : '-',
      });
    }

    return baseColumns;
  };

  return (
    <div className="asset-screener">
      <Card
        title={
          <Space>
            <span>{title || `${assetType?.toUpperCase()} 筛选器`}</span>
            {assetType && <Tag color="processing">{assetType}</Tag>}
          </Space>
        }
        loading={criteriaLoading}
      >
        {renderCriteriaForm()}
      </Card>

      {results.length > 0 && (
        <Card
          title={`筛选结果 (${pagination.total} 条)`}
          style={{ marginTop: 24 }}
        >
          <Table
            columns={getTableColumns()}
            dataSource={results}
            rowKey="symbol"
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) =>
                `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            }}
            onChange={handleTableChange}
            loading={loading}
            scroll={{ x: 1200 }}
            size="small"
          />
        </Card>
      )}
    </div>
  );
};

export default AssetScreener;
