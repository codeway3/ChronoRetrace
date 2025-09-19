import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { authApi, authUtils } from '../api/authApi';
import { message } from 'antd';

// 初始状态
const initialState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null
};

// Action类型
const AUTH_ACTIONS = {
  LOGIN_START: 'LOGIN_START',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGIN_FAILURE: 'LOGIN_FAILURE',
  LOGOUT: 'LOGOUT',
  LOAD_USER_START: 'LOAD_USER_START',
  LOAD_USER_SUCCESS: 'LOAD_USER_SUCCESS',
  LOAD_USER_FAILURE: 'LOAD_USER_FAILURE',
  UPDATE_USER: 'UPDATE_USER',
  CLEAR_ERROR: 'CLEAR_ERROR'
};

// Reducer函数
const authReducer = (state, action) => {
  switch (action.type) {
    case AUTH_ACTIONS.LOGIN_START:
    case AUTH_ACTIONS.LOAD_USER_START:
      return {
        ...state,
        isLoading: true,
        error: null
      };

    case AUTH_ACTIONS.LOGIN_SUCCESS:
    case AUTH_ACTIONS.LOAD_USER_SUCCESS:
      return {
        ...state,
        user: action.payload,
        isAuthenticated: true,
        isLoading: false,
        error: null
      };

    case AUTH_ACTIONS.LOGIN_FAILURE:
    case AUTH_ACTIONS.LOAD_USER_FAILURE:
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload
      };

    case AUTH_ACTIONS.LOGOUT:
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null
      };

    case AUTH_ACTIONS.UPDATE_USER:
      return {
        ...state,
        user: { ...state.user, ...action.payload }
      };

    case AUTH_ACTIONS.CLEAR_ERROR:
      return {
        ...state,
        error: null
      };

    default:
      return state;
  }
};

// 创建Context
const AuthContext = createContext();

// AuthProvider组件
export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // 加载用户信息
  const loadUser = async () => {
    if (!authUtils.isAuthenticated()) {
      dispatch({ type: AUTH_ACTIONS.LOAD_USER_FAILURE, payload: 'No token found' });
      return;
    }

    try {
      dispatch({ type: AUTH_ACTIONS.LOAD_USER_START });
      const response = await authApi.getCurrentUser();
      const user = response.data;

      authUtils.saveUserInfo(user);
      dispatch({ type: AUTH_ACTIONS.LOAD_USER_SUCCESS, payload: user });
    } catch (error) {
      console.error('Failed to load user:', error);
      authUtils.clearAuth();
      dispatch({ type: AUTH_ACTIONS.LOAD_USER_FAILURE, payload: error.message });
    }
  };

  // 登录
  const login = async (credentials) => {
    try {
      dispatch({ type: AUTH_ACTIONS.LOGIN_START });
      const response = await authApi.login(credentials);
      const { access_token, refresh_token, user } = response.data;

      authUtils.saveTokens(access_token, refresh_token);
      authUtils.saveUserInfo(user);

      dispatch({ type: AUTH_ACTIONS.LOGIN_SUCCESS, payload: user });
      message.success('登录成功！');

      return { success: true };
    } catch (error) {
      let errorMessage = '登录失败，请检查用户名和密码';

      if (error.response?.data) {
        const errorData = error.response.data;

        // 处理Pydantic验证错误
        if (Array.isArray(errorData.detail)) {
          // 格式化验证错误信息
          const validationErrors = errorData.detail.map(err => {
            const field = err.loc ? err.loc[err.loc.length - 1] : '字段';
            return `${field}: ${err.msg}`;
          }).join('; ');
          errorMessage = validationErrors;
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
      }

      dispatch({ type: AUTH_ACTIONS.LOGIN_FAILURE, payload: errorMessage });
      message.error(errorMessage);

      return { success: false, error: errorMessage };
    }
  };

  // 注册
  const register = async (userData) => {
    try {
      const response = await authApi.register(userData);
      message.success('注册成功！请检查邮箱进行验证。');
      return { success: true, data: response.data };
    } catch (error) {
      let errorMessage = '注册失败，请稍后重试';

      if (error.response?.data) {
        const errorData = error.response.data;

        // 处理Pydantic验证错误
        if (Array.isArray(errorData.detail)) {
          // 格式化验证错误信息
          const validationErrors = errorData.detail.map(err => {
            const field = err.loc ? err.loc[err.loc.length - 1] : '字段';
            return `${field}: ${err.msg}`;
          }).join('; ');
          errorMessage = validationErrors;
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
      }

      message.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // 登出
  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      authUtils.clearAuth();
      dispatch({ type: AUTH_ACTIONS.LOGOUT });
      message.success('已成功登出');
    }
  };

  // 更新用户资料
  const updateProfile = async (userData) => {
    try {
      const response = await authApi.updateProfile(userData);
      const updatedUser = response.data;

      authUtils.saveUserInfo(updatedUser);
      dispatch({ type: AUTH_ACTIONS.UPDATE_USER, payload: updatedUser });
      message.success('资料更新成功！');

      return { success: true, data: updatedUser };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || '更新失败，请稍后重试';
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // 修改密码
  const changePassword = async (passwordData) => {
    try {
      await authApi.changePassword(passwordData);
      message.success('密码修改成功！');
      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || '密码修改失败，请稍后重试';
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // 忘记密码
  const forgotPassword = async (email) => {
    try {
      await authApi.forgotPassword(email);
      message.success('密码重置邮件已发送，请检查邮箱！');
      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || '发送失败，请稍后重试';
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // 重置密码
  const resetPassword = async (token, newPassword) => {
    try {
      await authApi.resetPassword(token, newPassword);
      message.success('密码重置成功！请使用新密码登录。');
      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.detail || '密码重置失败，请稍后重试';
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  // 清除错误
  const clearError = () => {
    dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });
  };

  // 组件挂载时加载用户信息
  useEffect(() => {
    loadUser();
  }, []);

  const value = {
    ...state,
    login,
    register,
    logout,
    updateProfile,
    changePassword,
    forgotPassword,
    resetPassword,
    loadUser,
    clearError
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// 自定义Hook
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
