import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getDefaultStocks = () => {
  return apiClient.get('/stocks/list/default');
};

export const getAllStocks = () => {
    return apiClient.get('/stocks/list/all');
};

export const getStockData = (tsCode, interval = 'daily') => {
  return apiClient.get(`/stocks/${tsCode}?interval=${interval}`);
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
