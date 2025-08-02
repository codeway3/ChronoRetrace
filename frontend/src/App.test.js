import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

test('renders main layout and navigates to A-share dashboard by default', () => {
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>
  );

  // Check if the main layout's header is present
  const headerElement = screen.getByText(/ChronoRetrace/i);
  expect(headerElement).toBeInTheDocument();

  // Check if the A-Share Dashboard title is rendered as it's the default route
  const dashboardTitle = screen.getByText(/A股总览/i);
  expect(dashboardTitle).toBeInTheDocument();
});

test('renders US Stock Dashboard on navigation', () => {
  render(
    <MemoryRouter initialEntries={['/us-stock']}>
      <App />
    </MemoryRouter>
  );

  // Check if the US Stock Dashboard title is rendered
  const dashboardTitle = screen.getByText(/美股总览/i);
  expect(dashboardTitle).toBeInTheDocument();
});