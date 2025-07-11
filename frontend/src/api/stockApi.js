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
