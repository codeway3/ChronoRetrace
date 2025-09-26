import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Alert, Card, Typography } from 'antd';
import debounce from 'lodash.debounce';

import FilterBuilder from '../components/FilterBuilder';
import DataTable from '../components/DataTable';
import { screenStocks } from '../api/stockApi'; // This will be created next

const { Title, Paragraph } = Typography;

/**
 * The main page for the Stock Screener feature.
 * It orchestrates the FilterBuilder and DataTable components, manages state,
 * and handles API communication.
 */
const ScreenerPage = () => {
    const [conditions, setConditions] = useState([]);
    const [results, setResults] = useState([]);
    const [pagination, setPagination] = useState({
        current: 1,
        pageSize: 20,
        total: 0,
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Use ref to track current page to avoid dependency issues
    const currentPageRef = useRef(1);
    const pageSizeRef = useRef(20);

    // Update refs when pagination changes
    useEffect(() => {
        currentPageRef.current = pagination.current;
        pageSizeRef.current = pagination.pageSize;
    }, [pagination]);

    // Memoized fetch function to avoid re-creation on every render
    const fetchResults = useCallback(async (currentConditions, currentPage, pageSize) => {
        const validConditions = currentConditions.filter(c => c.value !== null && c.value !== '');
        if (validConditions.length === 0) {
            setResults([]);
            setPagination(prev => ({ ...prev, total: 0, current: 1 }));
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const request = {
                market: 'A_share', // This could be a dropdown in the UI in the future
                conditions: validConditions.map(c => ({ ...c, value: parseFloat(c.value) })),
                page: currentPage,
                size: pageSize,
            };
            const response = await screenStocks(request);
            const data = response.data; // Extract data from axios response
            setResults(data.items);
            setPagination(prev => ({ ...prev, total: data.total, current: data.page }));
        } catch (err) {
            setError('筛选股票失败，请检查网络或联系管理员。');
            console.error("Failed to screen stocks:", err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Debounced version of the fetch function to prevent excessive API calls
    const debouncedFetch = useMemo(() => debounce(fetchResults, 500), [fetchResults]);

    // Effect for conditions and page size changes
    useEffect(() => {
        debouncedFetch(conditions, currentPageRef.current, pageSizeRef.current);
        return () => debouncedFetch.cancel();
    }, [conditions, debouncedFetch]);

    // Effect for page number changes - only when conditions exist
    useEffect(() => {
        if (conditions.length > 0) {
            fetchResults(conditions, currentPageRef.current, pageSizeRef.current);
        }
    }, [fetchResults, conditions]);

    const handleConditionsChange = (newConditions) => {
        setConditions(newConditions);
        if (pagination.current !== 1) {
            setPagination(prev => ({ ...prev, current: 1 }));
        }
    };

    const handlePageChange = (newPage) => {
        setPagination(prev => ({ ...prev, current: newPage }));
    };

    const columns = [
        { title: '代码', dataIndex: 'code', key: 'code', sorter: (a, b) => a.code.localeCompare(b.code) },
        { title: '名称', dataIndex: 'name', key: 'name', sorter: (a, b) => a.name.localeCompare(b.name) },
        { title: '市盈率', dataIndex: 'pe_ratio', key: 'pe_ratio', sorter: (a, b) => (a.pe_ratio || 0) - (b.pe_ratio || 0), render: val => val ? val.toFixed(2) : 'N/A' },
        {
            title: '总市值',
            dataIndex: 'market_cap',
            key: 'market_cap',
            sorter: (a, b) => (a.market_cap || 0) - (b.market_cap || 0),
            render: (cap) => cap ? (cap / 100000000).toFixed(2) + ' 亿' : 'N/A'
        },
    ];

    return (
        <div style={{ padding: '20px' }}>
            <Card style={{ marginBottom: '20px' }}>
                <Title level={2}>股票筛选器</Title>
                <Paragraph>
                    通过组合不同的筛选条件来发现符合您投资策略的股票。所有条件将以“与”(AND)的逻辑进行组合。
                </Paragraph>
            </Card>

            <Card title="筛选条件" style={{ marginBottom: '20px' }}>
                <FilterBuilder onConditionsChange={handleConditionsChange} />
            </Card>

            <Card title={`筛选结果 (共 ${pagination.total} 条)`}>
                {error && <Alert message={error} type="error" style={{ marginBottom: '20px' }} showIcon />}
                <DataTable
                    columns={columns}
                    data={results}
                    loading={loading}
                    pagination={pagination}
                    onPageChange={handlePageChange}
                />
            </Card>
        </div>
    );
};

export default ScreenerPage;
