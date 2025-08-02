// src/setupTests.js
import '@testing-library/jest-dom';
import { message } from 'antd';

// 调试日志
console.log('src/setupTests.js is loaded');

// 模拟 window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => {
    const mediaQueryList = {
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(), // 兼容旧版 API
      removeListener: jest.fn(), // 兼容旧版 API
      addEventListener: jest.fn((event, handler) => {
        if (event === 'change') mediaQueryList.onchange = handler;
      }),
      removeEventListener: jest.fn((event, handler) => {
        if (event === 'change' && mediaQueryList.onchange === handler) {
          mediaQueryList.onchange = null;
        }
      }),
      dispatchEvent: jest.fn(),
    };
    return mediaQueryList;
  }),
});

// 模拟 document
if (typeof document === 'undefined') {
  global.document = {
    createDocumentFragment: jest.fn(() => ({
      appendChild: jest.fn(),
      removeChild: jest.fn(),
    })),
    createElement: jest.fn(() => ({
      className: '',
      style: {},
      appendChild: jest.fn(),
      removeChild: jest.fn(),
    })),
    body: {
      appendChild: jest.fn(),
      removeChild: jest.fn(),
    },
  };
}

// 模拟 ResizeObserver（用于 ECharts）
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// 模拟 antd message
jest.spyOn(message, 'error').mockImplementation(() => {});
jest.spyOn(message, 'success').mockImplementation(() => {});
jest.spyOn(message, 'warning').mockImplementation(() => {});