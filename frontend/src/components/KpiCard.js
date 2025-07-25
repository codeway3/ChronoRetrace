import React from 'react';
import './KpiCard.css';

const KpiCard = ({ title, value, format, market = 'US_stock', isDrawdown = false }) => {

    const formatValue = () => {
        if (value === null || value === undefined || typeof value !== 'number') return 'N/A';

        switch (format) {
            case 'currency':
                const currencySymbol = market === 'A_share' ? '¥' : '$';
                const absValue = Math.abs(value);

                if (absValue >= 1e9) { // Billions
                    return `${currencySymbol}${(value / 1e9).toFixed(2)}B`;
                }
                if (absValue >= 1e6) { // Millions
                    return `${currencySymbol}${(value / 1e6).toFixed(2)}M`;
                }
                if (absValue >= 10000) { // Thousands
                    return `${currencySymbol}${(value / 1000).toFixed(1)}K`;
                }
                return `${currencySymbol}${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            
            case 'percent':
                return `${(value * 100).toFixed(2)}%`;
            
            case 'number':
                return value.toLocaleString();
            
            default:
                return value;
        }
    };

    const getValueClassName = () => {
        let className = 'kpi-value';
        if (typeof value !== 'number' || value === 0) return className;

        const isPositive = value > 0;
        
        if (isDrawdown) {
            className += market === 'A_share' ? ' negative-a' : ' negative-us';
            return className;
        }

        if (market === 'A_share') {
            className += isPositive ? ' positive-a' : ' negative-a';
        } else {
            className += isPositive ? ' positive-us' : ' negative-us';
        }
        return className;
    };

    return (
        <div className="kpi-card">
            <div className="kpi-title">{title}</div>
            <div className={getValueClassName()}>
                {formatValue()}
            </div>
        </div>
    );
};

export default KpiCard;
