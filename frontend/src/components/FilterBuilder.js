import React, { useState } from 'react';
import { Select, InputNumber, Button } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import './FilterBuilder.css';

const { Option } = Select;

// Define the metrics and operators available for filtering
const METRICS = [
    { value: 'pe_ratio', label: '市盈率 (P/E)' },
    { value: 'pb_ratio', label: '市净率 (P/B)' },
    { value: 'market_cap', label: '总市值' },
    { value: 'dividend_yield', label: '股息率' },
    { value: 'close_price', label: '股价' },
    { value: 'ma5', label: '5日均线' },
    { value: 'ma20', label: '20日均线' },
    { value: 'volume', label: '成交量' },
];

const OPERATORS = [
    { value: 'gt', label: '>' },
    { value: 'lt', label: '<' },
    { value: 'gte', label: '>=' },
    { value: 'lte', label: '<=' },
    { value: 'eq', label: '=' },
];

/**
 * A component that allows users to dynamically build a list of filtering conditions.
 */
const FilterBuilder = ({ onConditionsChange }) => {
    const [conditions, setConditions] = useState([]);

    const notifyParent = (updatedConditions) => {
        if (onConditionsChange) {
            onConditionsChange(updatedConditions);
        }
    };

    const addCondition = () => {
        const newCondition = { field: 'pe_ratio', operator: 'gt', value: 10 };
        const updatedConditions = [...conditions, newCondition];
        setConditions(updatedConditions);
        notifyParent(updatedConditions);
    };

    const updateCondition = (index, part, value) => {
        const updatedConditions = [...conditions];
        updatedConditions[index][part] = value;
        setConditions(updatedConditions);
        notifyParent(updatedConditions);
    };

    const removeCondition = (index) => {
        const updatedConditions = conditions.filter((_, i) => i !== index);
        setConditions(updatedConditions);
        notifyParent(updatedConditions);
    };

    return (
        <div className="filter-builder-container">
            {conditions.map((cond, index) => (
                <div key={index} className="filter-condition-row">
                    <Select
                        value={cond.field}
                        onChange={(value) => updateCondition(index, 'field', value)}
                        style={{ width: 150 }}
                    >
                        {METRICS.map(m => <Option key={m.value} value={m.value}>{m.label}</Option>)}
                    </Select>
                    <Select
                        value={cond.operator}
                        onChange={(value) => updateCondition(index, 'operator', value)}
                        style={{ width: 80 }}
                    >
                        {OPERATORS.map(o => <Option key={o.value} value={o.value}>{o.label}</Option>)}
                    </Select>
                    <InputNumber
                        value={cond.value}
                        onChange={(value) => updateCondition(index, 'value', value)}
                        placeholder="输入数值"
                        style={{ width: 120 }}
                    />
                    <Button
                        icon={<DeleteOutlined />}
                        onClick={() => removeCondition(index)}
                        danger
                    />
                </div>
            ))}
            <Button
                type="dashed"
                onClick={addCondition}
                icon={<PlusOutlined />}
            >
                添加筛选条件
            </Button>
        </div>
    );
};

export default FilterBuilder;
