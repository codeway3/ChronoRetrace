import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});



export const getAllStocks = (marketType = 'A_share') => {
    return apiClient.get(`/stocks/list/all?market_type=${marketType}`);
};

export const getStockData = (tsCode, interval = 'daily', dateStr = null, marketType = 'A_share') => {
  return apiClient.get(`/stocks/${tsCode}?interval=${interval}${dateStr ? `&trade_date=${dateStr}` : ''}&market_type=${marketType}`);
};

export const getFundamentalData = (symbol) => {
  return apiClient.get(`/stocks/${symbol}/fundamentals`);
};

export const getCorporateActions = (symbol) => {
  return apiClient.get(`/stocks/${symbol}/corporate-actions`);
};

export const getAnnualEarnings = (symbol) => {
  return apiClient.get(`/stocks/${symbol}/annual-earnings`);
};

export const clearCache = () => {
  return apiClient.post('/admin/clear-cache');
};

export const runBacktest = (config) => {
  return apiClient.post('/backtest/grid', config);
};

// Crypto APIs
export const getTopCryptos = () => {
  return apiClient.get('/crypto/top');
};

export const getCryptoHistory = (symbol, interval = 'daily') => {
  return apiClient.get(`/crypto/${symbol}/history?interval=${interval}`);
};
