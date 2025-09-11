import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import MainLayout from './layouts/MainLayout';
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
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Routes>
          {/* 公开路由 */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* 受保护的路由 */}
          <Route path="/" element={<Navigate to="/a-share" replace />} />
          <Route path="/a-share" element={
            <ProtectedRoute>
              <MainLayout><AShareDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/us-stock" element={
            <ProtectedRoute>
              <MainLayout><USStockDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/crypto" element={
            <ProtectedRoute>
              <MainLayout><CryptoDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/commodities" element={
            <ProtectedRoute>
              <MainLayout><CommodityDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/a-share/industries" element={
            <ProtectedRoute>
              <MainLayout><AIndustriesDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/futures" element={
            <ProtectedRoute>
              <MainLayout><FuturesDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/options" element={
            <ProtectedRoute>
              <MainLayout><OptionsDashboard /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/backtest" element={
            <ProtectedRoute>
              <MainLayout><BacktestPage /></MainLayout>
            </ProtectedRoute>
          } />
          <Route path="/screener" element={
            <ProtectedRoute>
              <MainLayout><ScreenerPage /></MainLayout>
            </ProtectedRoute>
          } />
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