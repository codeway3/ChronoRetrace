import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import AShareDashboard from './pages/AShareDashboard';
import USStockDashboard from './pages/USStockDashboard';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <MainLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/a-share" replace />} />
          <Route path="/a-share" element={<AShareDashboard />} />
          <Route path="/us-stock" element={<USStockDashboard />} />
        </Routes>
      </MainLayout>
    </BrowserRouter>
  );
}

export default App;