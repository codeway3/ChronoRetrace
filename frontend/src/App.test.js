import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

// 模拟组件
jest.mock('./components/StockChart', () => () => <div data-testid="stock-chart">Mocked StockChart</div>);
jest.mock('./components/FinancialOverviewAndActions', () => () => <div data-testid="financial-overview">Mocked FinancialOverviewAndActions</div>);

// 模拟所有可能触发 message 的 API
jest.mock('./api/stockApi', () => ({
  getAllStocks: jest.fn().mockResolvedValue({
    data: [
      { ts_code: '600519.SH', name: '贵州茅台' },
      { ts_code: 'AAPL', name: 'Apple Inc.' },
    ],
  }),
  getStockData: jest.fn().mockResolvedValue({
    data: [],
  }),
  getCorporateActions: jest.fn().mockResolvedValue({
    data: [],
    status: 200,
  }),
  getAnnualEarnings: jest.fn().mockResolvedValue({
    data: [],
    status: 200,
  }),
}));

test('renders main layout and navigates to A-share dashboard by default', async () => {
  render(
    <MemoryRouter initialEntries={['/']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </MemoryRouter>
  );

  await waitFor(
    () => {
      const headerElement = screen.getByText(/ChronoRetrace/i);
      expect(headerElement).toBeInTheDocument();
    },
    { timeout: 2000 }
  );

  await waitFor(
    () => {
      const dashboardTitle = screen.getByText(/A股市场分析/i);
      expect(dashboardTitle).toBeInTheDocument();
    },
    { timeout: 2000 }
  );
});

test('renders US Stock Dashboard on navigation', async () => {
  render(
    <MemoryRouter initialEntries={['/us-stock']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </MemoryRouter>
  );

  await waitFor(
    () => {
      const dashboardTitle = screen.getByText(/美股市场分析/i);
      expect(dashboardTitle).toBeInTheDocument();
    },
    { timeout: 2000 }
  );
});