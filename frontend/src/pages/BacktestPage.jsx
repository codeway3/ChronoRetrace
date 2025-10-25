import React, { useState, useEffect } from 'react';
import { Form, Select, InputNumber, DatePicker, Button, Tooltip, Row, Col, message, Spin, Alert, Radio, Table } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { runBacktest, getAllStocks, runGridOptimization } from '../api/stockApi';
import KpiCard from '../components/KpiCard';
import TransactionsTable from '../components/TransactionsTable';
import BacktestChart from '../components/BacktestChart';
import './BacktestPage.css';

const { RangePicker } = DatePicker;
const { Option } = Select;

const BacktestPage = () => {
    const [form] = Form.useForm();
    const [aShareList, setAShareList] = useState([]);
    const [stockInfo, setStockInfo] = useState({ code: '000001.SZ', name: '', market: 'A_share' });
    const [results, setResults] = useState(null);
    const [optimizationResults, setOptimizationResults] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [mode, setMode] = useState('single'); // 'single' or 'optimize'

    useEffect(() => {
        const fetchStocks = async () => {
            try {
                const response = await getAllStocks('A_share');
                const formattedStocks = response.data.map(stock => ({
                    label: `${stock.name} (${stock.ts_code})`,
                    value: stock.ts_code,
                    name: stock.name,
                }));
                setAShareList(formattedStocks);
                if (formattedStocks.length > 0) {
                    setStockInfo({ code: formattedStocks[0].value, name: formattedStocks[0].name, market: 'A_share' });
                }
            } catch (err) {
                message.error("无法加载A股列表。");
            }
        };
        fetchStocks();
    }, []);

    const onFinish = async (values) => {
        let config = {
            ...values,
            start_date: values.date_range[0].format('YYYY-MM-DD'),
            end_date: values.date_range[1].format('YYYY-MM-DD'),
            initial_quantity: values.initial_quantity || 0,
            initial_per_share_cost: values.initial_per_share_cost || 0,
            // Convert percentages from form to decimals for backend
            commission_rate: (values.commission_rate || 0) / 100,
            stamp_duty_rate: (values.stamp_duty_rate || 0) / 100,
        };
        delete config.date_range;

        // For optimization mode, convert ranges
        if (mode === 'optimize') {
            if (values.upper_price_enable) {
                config.upper_price = [values.upper_price_start, values.upper_price_end, values.upper_price_step];
            } else {
                config.upper_price = values.upper_price;
            }

            if (values.lower_price_enable) {
                config.lower_price = [values.lower_price_start, values.lower_price_end, values.lower_price_step];
            } else {
                config.lower_price = values.lower_price;
            }

            if (values.grid_count_enable) {
                config.grid_count = [values.grid_count_start, values.grid_count_end, values.grid_count_step];
            } else {
                config.grid_count = values.grid_count;
            }
        }

        setIsLoading(true);
        setError(null);
        setResults(null);
        setOptimizationResults(null);

        try {
            let response;
            if (mode === 'optimize') {
                response = await runGridOptimization(config);
                setOptimizationResults(response.data);
            } else {
                response = await runBacktest(config);
                setResults(response.data);
                setStockInfo(prev => ({ ...prev, market: response.data.market_type }));
            }
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'An unknown error occurred.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleStockChange = (value, option) => {
        const isAShare = value.includes('.SH') || value.includes('.SZ');
        const market = isAShare ? 'A_share' : 'US_stock';
        const name = option ? option.name : value;
        setStockInfo({ code: value, name: name, market: market });
    };

    const currencySymbol = stockInfo.market === 'A_share' ? '¥' : '$';

    const initialValues = {
        // stock_code: '000001.SZ', // 移除默认选中，保持为空以强制用户选择
        date_range: [dayjs().subtract(2, 'year').startOf('year'), dayjs()],
        lower_price: 10,
        upper_price: 15,
        grid_count: 10,
        total_investment: 100000,
        initial_quantity: 0,
        initial_per_share_cost: 0,
        on_exceed_upper: 'hold',
        on_fall_below_lower: 'hold',
        commission_rate: 0.03, //万三
        min_commission: 5,
        stamp_duty_rate: 0.1, //千一
        // Optimization defaults
        upper_price_enable: false,
        upper_price_start: 12,
        upper_price_end: 18,
        upper_price_step: 2,
        lower_price_enable: false,
        lower_price_start: 8,
        lower_price_end: 12,
        lower_price_step: 2,
        grid_count_enable: false,
        grid_count_start: 5,
        grid_count_end: 15,
        grid_count_step: 5,
    };

    const renderRangeInput = (paramName, label, tooltip, min = 0, max, addonBefore) => {
        const enableField = `${paramName}_enable`;
        const startField = `${paramName}_start`;
        const endField = `${paramName}_end`;
        const stepField = `${paramName}_step`;

        return (
            <Form.Item
                label={<span>{label} <Tooltip title={tooltip}><QuestionCircleOutlined /></Tooltip></span>}
                required
            >
                <Form.Item name={enableField} style={{ marginBottom: 16 }}>
                    <Radio.Group>
                        <Radio value={false}>固定值</Radio>
                        <Radio value={true}>范围优化</Radio>
                    </Radio.Group>
                </Form.Item>

                <Form.Item shouldUpdate={(prevValues, currentValues) =>
                    prevValues[enableField] !== currentValues[enableField]
                } noStyle>
                    {({ getFieldValue }) => {
                        const enableRange = getFieldValue(enableField);

                        if (enableRange) {
                            return (
                                <div style={{ marginTop: 8 }}>
                                    <Row gutter={16}>
                                        <Col xs={24} sm={8}>
                                            <Form.Item
                                                name={startField}
                                                label="起始值"
                                                rules={[{ required: true, message: '请输入起始值' }]}
                                                style={{ marginBottom: 0 }}
                                                required
                                            >
                                                <InputNumber
                                                    style={{ width: '100%' }}
                                                    min={min}
                                                    max={max}
                                                    addonBefore={addonBefore}
                                                    placeholder="起始值"
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col xs={24} sm={8}>
                                            <Form.Item
                                                name={endField}
                                                label="结束值"
                                                rules={[{ required: true, message: '请输入结束值' }]}
                                                style={{ marginBottom: 0 }}
                                                required
                                            >
                                                <InputNumber
                                                    style={{ width: '100%' }}
                                                    min={min}
                                                    max={max}
                                                    addonBefore={addonBefore}
                                                    placeholder="结束值"
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col xs={24} sm={8}>
                                            <Form.Item
                                                name={stepField}
                                                label="步长"
                                                rules={[{ required: true, message: '请输入步长' }]}
                                                style={{ marginBottom: 0 }}
                                                required
                                            >
                                                <InputNumber
                                                    style={{ width: '100%' }}
                                                    min={0.01}
                                                    addonBefore={addonBefore}
                                                    placeholder="步长"
                                                />
                                            </Form.Item>
                                        </Col>
                                    </Row>
                                </div>
                            );
                        } else {
                            return (
                                <Form.Item
                                    name={paramName}
                                    rules={[{ required: true, message: `请输入${label}` }]}
                                    style={{ marginTop: 8 }}
                                    required
                                >
                                    <InputNumber
                                        style={{ width: '100%' }}
                                        min={min}
                                        max={max}
                                        addonBefore={addonBefore}
                                        placeholder={`请输入${label}`}
                                    />
                                </Form.Item>
                            );
                        }
                    }}
                </Form.Item>
            </Form.Item>
        );
    };

    return (
        <div className="backtest-page-container">
            <h1>网格交易回测</h1>

            <div style={{ marginBottom: 24 }}>
                <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)}>
                    <Radio value="single">单次回测</Radio>
                    <Radio value="optimize">参数优化</Radio>
                </Radio.Group>
            </div>

            <div className="form-container">
                <Form form={form} layout="vertical" onFinish={onFinish} initialValues={initialValues}>
                    <Row gutter={24}>
                        {/* Core Params */}
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="stock_code" label="股票代码" rules={[{ required: true, message: '请输入或选择股票代码' }]} required>
                                <Select showSearch placeholder="选择A股或输入美股代码" optionFilterProp="label" onChange={handleStockChange} options={aShareList} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="date_range" label="回测周期" rules={[{ required: true, message: '请输入回测周期' }]} required>
                                <RangePicker style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="total_investment" label={<span>网格策略资金 <Tooltip title="用于网格交易的现金总额"><QuestionCircleOutlined /></Tooltip></span>} rules={[{ required: true, message: '请输入总投资额' }]} required>
                                <InputNumber style={{ width: '100%' }} min={1} addonBefore={currencySymbol} formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={value => value.replace(/\$\s?|(,*)/g, '')} />
                            </Form.Item>
                        </Col>

                        {/* Grid Params */}
                        {mode === 'single' ? (
                            <>
                                <Col xs={24} sm={12} md={8}>
                                    <Form.Item name="lower_price" label={<span>价格下限 <Tooltip title="网格的最低价格"><QuestionCircleOutlined /></Tooltip></span>} rules={[{ required: true, message: '请输入价格下限' }]} required>
                                        <InputNumber style={{ width: '100%' }} min={0} />
                                    </Form.Item>
                                </Col>
                                <Col xs={24} sm={12} md={8}>
                                    <Form.Item name="upper_price" label={<span>价格上限 <Tooltip title="网格的最高价格"><QuestionCircleOutlined /></Tooltip></span>} rules={[{ required: true, message: '请输入价格上限' }]} required>
                                        <InputNumber style={{ width: '100%' }} min={0} />
                                    </Form.Item>
                                </Col>
                                <Col xs={24} sm={12} md={8}>
                                    <Form.Item name="grid_count" label={<span>网格数量 <Tooltip title="在价格上下限之间划分的网格数量"><QuestionCircleOutlined /></Tooltip></span>} rules={[{ required: true, message: '请输入网格数量' }]} required>
                                        <InputNumber style={{ width: '100%' }} min={0} max={100} />
                                    </Form.Item>
                                </Col>
                            </>
                        ) : (
                            <>
                                <Col xs={24} lg={8}>
                                    {renderRangeInput('lower_price', '价格下限', '网格的最低价格', 0)}
                                </Col>
                                <Col xs={24} lg={8}>
                                    {renderRangeInput('upper_price', '价格上限', '网格的最高价格', 0)}
                                </Col>
                                <Col xs={24} lg={8}>
                                    {renderRangeInput('grid_count', '网格数量', '在价格上下限之间划分的网格数量', 1, 100)}
                                </Col>
                            </>
                        )}

                        {/* Initial Position Params */}
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="initial_quantity" label={<span>初始持股 (选填) <Tooltip title="回测开始时已持有的股票数量。默认为0。"><QuestionCircleOutlined /></Tooltip></span>}>
                                <InputNumber style={{ width: '100%' }} min={0} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="initial_per_share_cost" label={<span>每股成本 (选填) <Tooltip title="初始持股的每股成本价。用于精确计算盈亏。"><QuestionCircleOutlined /></Tooltip></span>}>
                                <InputNumber style={{ width: '100%' }} min={0} addonBefore={currencySymbol} formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={value => value.replace(/\$\s?|(,*)/g, '')} />
                            </Form.Item>
                        </Col>
                        <Col span={8} />

                        {/* Out-of-Bounds Strategy Params */}
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="on_exceed_upper" label={<span>突破上限时 <Tooltip title="当股价超过网格上限时的操作策略"><QuestionCircleOutlined /></Tooltip></span>}>
                                <Select>
                                    <Option value="hold">持有不动</Option>
                                    <Option value="sell_all">清仓止盈</Option>
                                </Select>
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="on_fall_below_lower" label={<span>跌破下限时 <Tooltip title="当股价跌破网格下限时的操作策略"><QuestionCircleOutlined /></Tooltip></span>}>
                                <Select>
                                    <Option value="hold">持有不动</Option>
                                    <Option value="sell_all">清仓止损</Option>
                                </Select>
                            </Form.Item>
                        </Col>
                    </Row>
                    <Row gutter={24} style={{ marginTop: '24px' }}>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="commission_rate" label={<span>佣金费率 (%) <Tooltip title="单边交易佣金的百分比。例如，0.03 代表万分之三。"><QuestionCircleOutlined /></Tooltip></span>} required>
                                <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="min_commission" label={<span>最低佣金 <Tooltip title="每笔交易的最低佣金费用。"><QuestionCircleOutlined /></Tooltip></span>} required>
                                <InputNumber style={{ width: '100%' }} min={0} addonBefore={currencySymbol} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="stamp_duty_rate" label={<span>印花税率 (%) <Tooltip title="卖出时收取的印花税百分比。A股通常为0.1% (千分之一)。"><QuestionCircleOutlined /></Tooltip></span>} required>
                                <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item>
                        <Button type="primary" htmlType="submit" loading={isLoading}>
                            {mode === 'single' ? '开始回测' : '开始优化'}
                        </Button>
                    </Form.Item>
                </Form>
            </div>

            {isLoading && <div className="spinner-container"><Spin size="large" /></div>}
            {error && <Alert message="回测出错" description={error} type="error" showIcon closable onClose={() => setError(null)} />}

            {results && (
                <div className="results-container">
                    <h2>回测结果: { (stockInfo?.name ? stockInfo.name : '—') } ({ (stockInfo?.code ? stockInfo.code : '—') })</h2>
                    <Row gutter={[16, 16]} className="kpi-grid">
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="总盈亏" value={results.total_pnl} format="currency" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="总回报率" value={results.total_return_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="年化回报率" value={results.annualized_return_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="年化波动率" value={results.annualized_volatility} format="percent" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="夏普比率" value={results.sharpe_ratio} format="number" /></Col>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="最大回撤" value={results.max_drawdown} format="percent" isDrawdown={true} market={results.market_type} /></Col>
                    </Row>
                    <Row gutter={[16, 16]} className="kpi-grid" style={{ marginTop: '16px' }}>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="胜率" value={results.win_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="交易次数" value={results.trade_count} format="number" /></Col>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="期末持仓" value={results.final_holding_quantity} format="number" /></Col>
                        <Col xs={12} sm={12} md={6} lg={4}><KpiCard title="持仓均价" value={results.average_holding_cost} format="currency" market={results.market_type} /></Col>
                    </Row>

                    <div className="chart-container">
                        <h3>策略表现 vs. 基准</h3>
                        <BacktestChart
                            klineData={results.kline_data}
                            portfolioData={results.chart_data}
                            transactions={results.transaction_log}
                            stockCode={stockInfo.code}
                            stockName={stockInfo.name}
                            marketType={results.market_type}
                        />
                    </div>

                    <TransactionsTable transactions={results.transaction_log} market={results.market_type} />
                </div>
            )}

            {optimizationResults && (
                <div className="results-container">
                    <h2>参数优化结果: { (stockInfo?.name ? stockInfo.name : '—') } ({ (stockInfo?.code ? stockInfo.code : '—') })</h2>

                    <div style={{ marginBottom: 24 }}>
                        <h3>最佳参数组合</h3>
                        <Row gutter={[16, 16]} className="kpi-grid">
                            <Col xs={12} sm={8} md={6}>
                                <KpiCard title="价格上限" value={optimizationResults.best_result.parameters.upper_price} format="currency" market={stockInfo.market} />
                            </Col>
                            <Col xs={12} sm={8} md={6}>
                                <KpiCard title="价格下限" value={optimizationResults.best_result.parameters.lower_price} format="currency" market={stockInfo.market} />
                            </Col>
                            <Col xs={12} sm={8} md={6}>
                                <KpiCard title="网格数量" value={optimizationResults.best_result.parameters.grid_count} format="number" />
                            </Col>
                            <Col xs={12} sm={8} md={6}>
                                <KpiCard title="年化收益率" value={optimizationResults.best_result.annualized_return_rate} format="percent" market={stockInfo.market} />
                            </Col>
                            <Col xs={12} sm={8} md={6}>
                                <KpiCard title="夏普比率" value={optimizationResults.best_result.sharpe_ratio} format="number" />
                            </Col>
                            <Col xs={12} sm={8} md={6}>
                                <KpiCard title="最大回撤" value={optimizationResults.best_result.max_drawdown} format="percent" isDrawdown={true} market={stockInfo.market} />
                            </Col>
                        </Row>
                    </div>

                    <div>
                        <h3>所有优化结果 (共 {optimizationResults.optimization_results.length} 组)</h3>
                        <Table
                            dataSource={optimizationResults.optimization_results.map((item, index) => ({ ...item, key: index }))}
                            scroll={{ x: 800 }}
                            pagination={{ pageSize: 10, showSizeChanger: true }}
                            columns={[
                                { title: '排名', dataIndex: 'key', key: 'rank', render: (_, __, index) => index + 1, width: 60 },
                                { title: '价格上限', dataIndex: ['parameters', 'upper_price'], key: 'upper_price', render: (val) => currencySymbol + val.toFixed(2) },
                                { title: '价格下限', dataIndex: ['parameters', 'lower_price'], key: 'lower_price', render: (val) => currencySymbol + val.toFixed(2) },
                                { title: '网格数量', dataIndex: ['parameters', 'grid_count'], key: 'grid_count' },
                                { title: '年化收益率', dataIndex: 'annualized_return_rate', key: 'return', render: (val) => (val * 100).toFixed(2) + '%', sorter: (a, b) => a.annualized_return_rate - b.annualized_return_rate },
                                { title: '夏普比率', dataIndex: 'sharpe_ratio', key: 'sharpe', render: (val) => val.toFixed(4), sorter: (a, b) => a.sharpe_ratio - b.sharpe_ratio },
                                { title: '最大回撤', dataIndex: 'max_drawdown', key: 'drawdown', render: (val) => (val * 100).toFixed(2) + '%', sorter: (a, b) => a.max_drawdown - b.max_drawdown },
                                { title: '胜率', dataIndex: 'win_rate', key: 'win_rate', render: (val) => (val * 100).toFixed(2) + '%', sorter: (a, b) => a.win_rate - b.win_rate },
                                { title: '交易次数', dataIndex: 'trade_count', key: 'trades', sorter: (a, b) => a.trade_count - b.trade_count },
                            ]}
                        />
                    </div>
                </div>
            )}
        </div>
    );
};

export default BacktestPage;
