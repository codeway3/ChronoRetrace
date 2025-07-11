# ChronoRetrace - Frontend

This directory contains the React frontend for the ChronoRetrace application.

## Overview

The frontend is built with [React](https://reactjs.org/) and [Ant Design](https://ant.design/). It communicates with the backend API to fetch and display financial data.

### Key Technologies

- **Framework**: React
- **UI Component Library**: Ant Design
- **Charting Library**: ECharts for React
- **API Client**: Axios

## Getting Started

To run the frontend development server, follow these steps:

1.  **Install Dependencies**:
    ```bash
    # From the project root directory
    npm install --prefix frontend
    ```

2.  **Run the Development Server**:
    ```bash
    # From the project root directory
    npm start --prefix frontend
    ```
    The application will open automatically in your browser at `http://localhost:3000`.

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── api/              # API client for the backend
│   ├── components/       # Reusable React components
│   ├── layouts/          # Layout components
│   ├── pages/            # Page components
│   ├── App.js            # Main application component
│   └── index.js          # Entry point
└── package.json
```

## Available Scripts

In the `frontend` directory, you can run:

- `npm start`: Runs the app in development mode.
- `npm test`: Launches the test runner.
- `npm run build`: Builds the app for production.
- `npm run eject`: Ejects from Create React App.