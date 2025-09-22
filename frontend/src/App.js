import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import MainLayout from './layouts/MainLayout';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import ProtectedRoute from './components/ProtectedRoute';
import AShareDashboard from './pages/AShareDashboard';
import USStockDashboard from './pages/USStockDashboard';
import BacktestPage from './pages/BacktestPage';
import CryptoDashboard from './pages/CryptoDashboard';
import CommodityDashboard from './pages/CommodityDashboard';
import AIndustriesDashboard from './pages/AIndustriesDashboard';
import FuturesDashboard from './pages/FuturesDashboard';
import OptionsDashboard from './pages/OptionsDashboard';
import ScreenerPage from './pages/ScreenerPage';
import WebSocketTest from './pages/WebSocketTest';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Routes>
          {/* 公开路由 */}
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/websocket-test" element={<WebSocketTest />} />

          {/* 受保护的路由 - 按投资标的分类的二级层次化导航 */}

          {/* A股相关路由 */}
          <Route path="/a-share" element={
            <ProtectedRoute>
              <MainLayout><AShareDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/a-share/screener" element={
            <ProtectedRoute>
              <MainLayout><ScreenerPage assetType="a-share" /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/a-share/backtest" element={
            <ProtectedRoute>
              <MainLayout><BacktestPage assetType="a-share" /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/a-share/industries" element={
            <ProtectedRoute>
              <MainLayout><AIndustriesDashboard /></MainLayout>
            </ProtectedRoute>
          } />

          {/* 美股相关路由 */}
          <Route path="/us-stock" element={
            <ProtectedRoute>
              <MainLayout><USStockDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/us-stock/screener" element={
            <ProtectedRoute>
              <MainLayout><ScreenerPage assetType="us-stock" /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/us-stock/backtest" element={
            <ProtectedRoute>
              <MainLayout><BacktestPage assetType="us-stock" /></MainLayout>
            </ProtectedRoute>
          } />

          {/* 加密货币相关路由 */}
          <Route path="/crypto" element={
            <ProtectedRoute>
              <MainLayout><CryptoDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/crypto/screener" element={
            <ProtectedRoute>
              <MainLayout><ScreenerPage assetType="crypto" /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/crypto/backtest" element={
            <ProtectedRoute>
              <MainLayout><BacktestPage assetType="crypto" /></MainLayout>
            </ProtectedRoute>
          } />

          {/* 大宗商品相关路由 */}
          <Route path="/commodities" element={
            <ProtectedRoute>
              <MainLayout><CommodityDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/commodities/screener" element={
            <ProtectedRoute>
              <MainLayout><ScreenerPage assetType="commodities" /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/commodities/backtest" element={
            <ProtectedRoute>
              <MainLayout><BacktestPage assetType="commodities" /></MainLayout>
            </ProtectedRoute>
          } />

          {/* 期货相关路由 */}
          <Route path="/futures" element={
            <ProtectedRoute>
              <MainLayout><FuturesDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/futures/screener" element={
            <ProtectedRoute>
              <MainLayout><ScreenerPage assetType="futures" /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/futures/backtest" element={
            <ProtectedRoute>
              <MainLayout><BacktestPage assetType="futures" /></MainLayout>
            </ProtectedRoute>
          } />

          {/* 期权相关路由 */}
          <Route path="/options" element={
            <ProtectedRoute>
              <MainLayout><OptionsDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/options/screener" element={
            <ProtectedRoute>
              <MainLayout><ScreenerPage assetType="options" /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/options/backtest" element={
            <ProtectedRoute>
              <MainLayout><BacktestPage assetType="options" /></MainLayout>
            </ProtectedRoute>
          } />

          {/* 通用功能路由（保持向后兼容） */}
          <Route path="/screener" element={
            <ProtectedRoute>
              <MainLayout><ScreenerPage /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/backtest" element={
            <ProtectedRoute>
              <MainLayout><BacktestPage /></MainLayout>
            </ProtectedRoute>
          } />

          {/* 用户相关路由 */}
          <Route path="/profile" element={
            <ProtectedRoute>
              <MainLayout><ProfilePage /></MainLayout>
            </ProtectedRoute>
          } />
      </Routes>
    </AuthProvider>
  );
}

export default App;
