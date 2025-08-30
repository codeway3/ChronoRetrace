import React from 'react';
import { Table } from 'antd';

/**
 * A generic data table component for displaying, sorting, and paginating data.
 * Built on top of Ant Design's Table component.
 */
const DataTable = ({ columns, data, loading, pagination, onPageChange }) => {

    /**
     * Handles page changes from the Ant Design Table component.
     * @param {object} newPagination - The pagination object from antd.
     */
    const handleTableChange = (newPagination) => {
        if (onPageChange && newPagination.current !== pagination.current) {
            onPageChange(newPagination.current);
        }
    };

    return (
        <Table
            columns={columns}
            dataSource={data.map((item, index) => ({ ...item, key: index }))}
            loading={loading}
            pagination={pagination}
            onChange={handleTableChange}
            size="small"
            scroll={{ x: 'max-content' }}
            showSorterTooltip={false}
        />
    );
};

export default DataTable;
