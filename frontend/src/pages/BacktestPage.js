import React, { useState, useEffect } from 'react';
import { Form, Select, InputNumber, DatePicker, Button, Tooltip, Row, Col, message, Spin, Alert } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { runBacktest, getAllStocks } from '../api/stockApi';
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
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

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
        const config = {
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

        setIsLoading(true);
        setError(null);
        setResults(null);
        try {
            const response = await runBacktest(config);
            setResults(response.data);
            setStockInfo(prev => ({ ...prev, market: response.data.market_type }));
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
        stock_code: '000001.SZ',
        date_range: [dayjs('2022-01-01'), dayjs('2023-01-01')],
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
    };

    return (
        <div className="backtest-page-container">
            <h1>网格交易回测</h1>
            <div className="form-container">
                <Form form={form} layout="vertical" onFinish={onFinish} initialValues={initialValues}>
                    <Row gutter={24}>
                        {/* Core Params */}
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="stock_code" label="股票代码" rules={[{ required: true, message: '请输入或选择股票代码' }]}>
                                <Select showSearch placeholder="选择A股或输入美股代码" optionFilterProp="label" onChange={handleStockChange} options={aShareList} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="date_range" label="回测周期" rules={[{ required: true, message: '请选择回测周期' }]}>
                                <RangePicker style={{ width: '100%' }} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="total_investment" label={<span>网格策略资金 <Tooltip title="用于网格交易的现金总额"><QuestionCircleOutlined /></Tooltip></span>} rules={[{ required: true, message: '请输入总投资额' }]}>
                                <InputNumber style={{ width: '100%' }} min={1} addonBefore={currencySymbol} formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={value => value.replace(/\$\s?|(,*)/g, '')} />
                            </Form.Item>
                        </Col>
                        
                        {/* Grid Params */}
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="lower_price" label={<span>价格下限 <Tooltip title="网格的最低价格"><QuestionCircleOutlined /></Tooltip></span>} rules={[{ required: true, message: '请输入价格下限' }]}>
                                <InputNumber style={{ width: '100%' }} min={0} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="upper_price" label={<span>价格上限 <Tooltip title="网格的最高价格"><QuestionCircleOutlined /></Tooltip></span>} rules={[{ required: true, message: '请输入价格上限' }]}>
                                <InputNumber style={{ width: '100%' }} min={0} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="grid_count" label={<span>网格数量 <Tooltip title="在价格上下限之间划分的网格数量"><QuestionCircleOutlined /></Tooltip></span>} rules={[{ required: true, message: '请输入网格数量' }]}>
                                <InputNumber style={{ width: '100%' }} min={1} max={100} />
                            </Form.Item>
                        </Col>

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
                            <Form.Item name="commission_rate" label={<span>佣金费率 (%) <Tooltip title="单边交易佣金的百分比。例如，0.03 代表万分之三。"><QuestionCircleOutlined /></Tooltip></span>}>
                                <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="min_commission" label={<span>最低佣金 <Tooltip title="每笔交易的最低佣金费用。"><QuestionCircleOutlined /></Tooltip></span>}>
                                <InputNumber style={{ width: '100%' }} min={0} addonBefore={currencySymbol} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="stamp_duty_rate" label={<span>印花税率 (%) <Tooltip title="卖出时收取的印花税百分比。A股通常为0.1% (千分之一)。"><QuestionCircleOutlined /></Tooltip></span>}>
                                <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item>
                        <Button type="primary" htmlType="submit" loading={isLoading}>开始回测</Button>
                    </Form.Item>
                </Form>
            </div>

            {isLoading && <div className="spinner-container"><Spin size="large" /></div>}
            {error && <Alert message="回测出错" description={error} type="error" showIcon closable onClose={() => setError(null)} />}

            {results && (
                <div className="results-container">
                    <h2>回测结果: {stockInfo.name} ({stockInfo.code})</h2>
                    <Row gutter={[16, 16]} className="kpi-grid">
                        <Col xs={12} sm={12} md={6}><KpiCard title="总盈亏" value={results.total_pnl} format="currency" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6}><KpiCard title="总回报率" value={results.total_return_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6}><KpiCard title="年化回报率" value={results.annualized_return_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6}><KpiCard title="最大回撤" value={results.max_drawdown} format="percent" isDrawdown={true} market={results.market_type} /></Col>
                    </Row>
                    <Row gutter={[16, 16]} className="kpi-grid" style={{ marginTop: '16px' }}>
                        <Col xs={12} sm={12} md={6}><KpiCard title="胜率" value={results.win_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={12} sm={12} md={6}><KpiCard title="交易次数" value={results.trade_count} format="number" /></Col>
                        <Col xs={12} sm={12} md={6}><KpiCard title="期末持仓" value={results.final_holding_quantity} format="number" /></Col>
                        <Col xs={12} sm={12} md={6}><KpiCard title="持仓均价" value={results.average_holding_cost} format="currency" market={results.market_type} /></Col>
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
        </div>
    );
};

export default BacktestPage;