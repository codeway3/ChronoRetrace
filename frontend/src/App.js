import React from 'react';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import './App.css';

function App() {
  return (
    <MainLayout>
      <Dashboard />
    </MainLayout>
  );
}

export default App;