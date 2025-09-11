import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理token过期
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post('http://127.0.0.1:8000/api/v1/auth/refresh', {
            refresh_token: refreshToken
          });
          
          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);
          
          // 重试原请求
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          // refresh token也过期了，清除所有token并跳转到登录页
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user_info');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        // 没有refresh token，直接跳转到登录页
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

// 认证相关API
export const authApi = {
  // 用户注册
  register: (userData) => {
    return apiClient.post('/auth/register', userData);
  },

  // 用户登录
  login: (credentials) => {
    return apiClient.post('/auth/login', credentials);
  },

  // 用户登出
  logout: () => {
    return apiClient.post('/auth/logout');
  },

  // 刷新token
  refreshToken: (refreshToken) => {
    return apiClient.post('/auth/refresh', { refresh_token: refreshToken });
  },

  // 忘记密码
  forgotPassword: (email) => {
    return apiClient.post('/auth/forgot-password', { email });
  },

  // 重置密码
  resetPassword: (token, newPassword) => {
    return apiClient.post('/auth/reset-password', {
      token,
      new_password: newPassword
    });
  },

  // 邮箱验证
  verifyEmail: (token) => {
    return apiClient.post('/auth/verify-email', { token });
  },

  // 启用双因子认证
  enable2FA: () => {
    return apiClient.post('/auth/enable-2fa');
  },

  // 验证双因子认证
  verify2FA: (code) => {
    return apiClient.post('/auth/verify-2fa', { code });
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    return apiClient.get('/users/profile');
  },

  // 更新用户资料
  updateProfile: (userData) => {
    return apiClient.put('/users/profile', userData);
  },

  // 修改密码
  changePassword: (passwordData) => {
    return apiClient.post('/users/change-password', passwordData);
  },

  // 获取用户偏好设置
  getPreferences: () => {
    return apiClient.get('/users/preferences');
  },

  // 更新用户偏好设置
  updatePreferences: (preferences) => {
    return apiClient.put('/users/preferences', preferences);
  }
};

// 工具函数
export const authUtils = {
  // 检查是否已登录
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },

  // 获取当前用户信息
  getCurrentUser: () => {
    const userInfo = localStorage.getItem('user_info');
    return userInfo ? JSON.parse(userInfo) : null;
  },

  // 保存用户信息
  saveUserInfo: (userInfo) => {
    localStorage.setItem('user_info', JSON.stringify(userInfo));
  },

  // 清除认证信息
  clearAuth: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
  },

  // 保存token
  saveTokens: (accessToken, refreshToken) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }
};

export default apiClient;