import axios from 'axios';

const apiBaseURL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) || '/api/v1';

const apiClient = axios.create({
  baseURL: apiBaseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器以包含认证令牌
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 策略管理API
export const getAllStrategies = () => {
  return apiClient.get('/strategies');
};

export const getStrategyById = (id) => {
  return apiClient.get(`/strategies/${id}`);
};

export const createStrategy = (strategyData) => {
  return apiClient.post('/strategies', strategyData);
};

export const updateStrategy = (id, strategyData) => {
  return apiClient.put(`/strategies/${id}`, strategyData);
};

export const deleteStrategy = (id) => {
  return apiClient.delete(`/strategies/${id}`);
};

// 回测管理API
export const getAllBacktestResults = () => {
  return apiClient.get('/backtest/results');
};

export const getBacktestResultById = (id) => {
  return apiClient.get(`/backtest/results/${id}`);
};

export const runBacktest = (backtestConfig) => {
  return apiClient.post('/backtest/run', backtestConfig);
};

export const deleteBacktestResult = (id) => {
  return apiClient.delete(`/backtest/results/${id}`);
};

// 策略执行API
export const executeStrategy = (strategyId, symbol) => {
  return apiClient.post(`/strategies/${strategyId}/execute`, { symbol });
};

export const getStrategyExecutionHistory = (strategyId) => {
  return apiClient.get(`/strategies/${strategyId}/executions`);
};
