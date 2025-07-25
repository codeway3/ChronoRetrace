import React from 'react';
import { Table, Tag } from 'antd';
import './TransactionsTable.css';

const getPnlColor = (pnl, market) => {
    if (pnl === null || pnl === undefined || pnl === 0) return 'grey';
    
    const isPositive = pnl > 0;
    if (market === 'A_share') {
        return isPositive ? '#ff4d4f' : '#52c41a';
    }
    // Default to US market colors
    return isPositive ? '#28a745' : '#dc3545';
};

const TransactionsTable = ({ transactions, market = 'US_stock' }) => {
    if (!transactions || transactions.length === 0) {
        return (
            <div className="transactions-table-container">
                <h3>交易记录</h3>
                <p>本次回测没有发生交易。</p>
            </div>
        );
    }

    const currencySymbol = market === 'A_share' ? '¥' : '$';

    const columns = [
        { title: '日期', dataIndex: 'trade_date', key: 'date', width: 120, sorter: (a, b) => new Date(a.trade_date) - new Date(b.trade_date), defaultSortOrder: 'ascend' },
        { 
            title: '类型', 
            dataIndex: 'trade_type', 
            key: 'type', 
            width: 80,
            render: type => <Tag color={type === 'buy' ? 'green' : 'red'}>{type.toUpperCase()}</Tag>,
            filters: [
                { text: 'BUY', value: 'buy' },
                { text: 'SELL', value: 'sell' },
            ],
            onFilter: (value, record) => record.trade_type.indexOf(value) === 0,
        },
        { title: '价格', dataIndex: 'price', key: 'price', width: 100, render: price => `${currencySymbol}${price.toFixed(2)}` },
        { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 100, render: qty => qty.toLocaleString() },
        { 
            title: '盈亏 (PnL)', 
            dataIndex: 'pnl', 
            key: 'pnl', 
            width: 120,
            render: pnl => {
                if (pnl === null || pnl === undefined) return 'N/A';
                const color = getPnlColor(pnl, market);
                return <span style={{ color, fontWeight: 'bold' }}>{`${pnl > 0 ? '+' : ''}${currencySymbol}${pnl.toFixed(2)}`}</span>;
            },
            sorter: (a, b) => (a.pnl || 0) - (b.pnl || 0),
        },
    ];

    return (
        <div className="transactions-table-container">
            <h3>交易记录</h3>
            <Table 
                columns={columns} 
                dataSource={transactions.map((t, i) => ({ ...t, key: i }))} 
                pagination={{ pageSize: 10 }} 
                size="small"
                scroll={{ x: 'max-content' }}
            />
        </div>
    );
};

export default TransactionsTable;