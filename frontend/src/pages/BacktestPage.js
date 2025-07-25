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
    };

    return (
        <div className="backtest-page-container">
            <h1>网格交易回测</h1>
            <div className="form-container">
                <Form form={form} layout="vertical" onFinish={onFinish} initialValues={initialValues}>
                    <Row gutter={24}>
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
                                <InputNumber style={{ width: '100%' }} min={1} formatter={value => `${currencySymbol} ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={value => value.replace(new RegExp(`\\${currencySymbol}\\s?|(,*)/g`), '')} />
                            </Form.Item>
                        </Col>
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
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="initial_quantity" label={<span>初始持股 (选填) <Tooltip title="回测开始时已持有的股票数量。默认为0。"><QuestionCircleOutlined /></Tooltip></span>}>
                                <InputNumber style={{ width: '100%' }} min={0} />
                            </Form.Item>
                        </Col>
                        <Col xs={24} sm={12} md={8}>
                            <Form.Item name="initial_per_share_cost" label={<span>每股成本 (选填) <Tooltip title="初始持股的每股成本价。用于精确计算盈亏。"><QuestionCircleOutlined /></Tooltip></span>}>
                                <InputNumber style={{ width: '100%' }} min={0} formatter={value => `${currencySymbol} ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} parser={value => value.replace(new RegExp(`\\${currencySymbol}\\s?|(,*)/g`), '')} />
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
                        <Col xs={24} sm={12} md={8} lg={4}><KpiCard title="总盈亏" value={results.total_pnl} format="currency" market={results.market_type} /></Col>
                        <Col xs={24} sm={12} md={8} lg={4}><KpiCard title="总回报率" value={results.total_return_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={24} sm={12} md={8} lg={4}><KpiCard title="年化回报率" value={results.annualized_return_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={24} sm={12} md={8} lg={4}><KpiCard title="最大回撤" value={results.max_drawdown} format="percent" isDrawdown={true} market={results.market_type} /></Col>
                        <Col xs={24} sm={12} md={8} lg={4}><KpiCard title="胜率" value={results.win_rate} format="percent" market={results.market_type} /></Col>
                        <Col xs={24} sm={12} md={8} lg={4}><KpiCard title="交易次数" value={results.trade_count} format="number" /></Col>
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