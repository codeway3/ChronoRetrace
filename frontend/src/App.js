import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import AShareDashboard from './pages/AShareDashboard';
import USStockDashboard from './pages/USStockDashboard';
import BacktestPage from './pages/BacktestPage';
import CryptoDashboard from './pages/CryptoDashboard';
import CommodityDashboard from './pages/CommodityDashboard';
import AIndustriesDashboard from './pages/AIndustriesDashboard';
import FuturesDashboard from './pages/FuturesDashboard';
import OptionsDashboard from './pages/OptionsDashboard';
import './App.css';

function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/a-share" replace />} />
        <Route path="/a-share" element={<AShareDashboard />} />
        <Route path="/us-stock" element={<USStockDashboard />} />
        <Route path="/crypto" element={<CryptoDashboard />} />
        <Route path="/commodities" element={<CommodityDashboard />} />
        <Route path="/a-share/industries" element={<AIndustriesDashboard />} />
        <Route path="/futures" element={<FuturesDashboard />} />
        <Route path="/options" element={<OptionsDashboard />} />
        <Route path="/backtest" element={<BacktestPage />} />
      </Routes>
    </MainLayout>
  );
}

export default App;