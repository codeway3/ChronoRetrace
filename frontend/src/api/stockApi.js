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

export const runGridOptimization = (config) => {
  return apiClient.post('/backtest/grid/optimize', config);
};

// Crypto APIs
export const getTopCryptos = () => {
  return apiClient.get('/crypto/top');
};

export const getCryptoHistory = (symbol, interval = 'daily') => {
  return apiClient.get(`/crypto/${symbol}/history?interval=${interval}`);
};

// Commodity APIs
export const getCommodityList = () => {
  return apiClient.get('/commodities/list');
};

export const getCommodityData = (symbol, interval = 'daily') => {
  return apiClient.get(`/commodities/${symbol}?interval=${interval}`);
};

// Futures APIs
export const getFuturesList = () => {
  return apiClient.get('/futures/list');
};

export const getFuturesData = (symbol, interval = 'daily') => {
  return apiClient.get(`/futures/${symbol}?interval=${interval}`);
};

// Options APIs
export const getOptionExpirations = (underlyingSymbol) => {
  return apiClient.get(`/options/expirations/${underlyingSymbol}`);
};

export const getOptionChain = (underlyingSymbol, expirationDate) => {
  return apiClient.get(`/options/chain/${underlyingSymbol}?expiration_date=${expirationDate}`);
};

export const getOptionsData = (symbol, interval = 'daily', window = 'MAX') => {
  return apiClient.get(`/options/${symbol}?interval=${interval}&window=${window}`);
};

// A-share Industries APIs
export const getAIndustryList = (provider = 'em') => {
  return apiClient.get(`/a-industries/list?provider=${provider}`);
};

export const getAIndustryOverview = (window = '20D', provider = 'em') => {
  return apiClient.get(`/a-industries/overview?window=${window}&provider=${provider}`);
};

export const getAIndustryStocks = (industryCode) => {
  return apiClient.get(`/a-industries/${industryCode}/stocks`);
};
