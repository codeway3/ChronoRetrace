# ChronoRetrace - A Financial Backtesting Tool

ChronoRetrace is a web-based tool for backtesting financial market strategies. It provides a platform for quantitative analysts, investors, and researchers to fetch, store, visualize, and analyze historical financial data.

The initial focus is on the A-share market, but the architecture is designed to be extensible to other markets like Hong Kong stocks, US stocks, and cryptocurrencies.

## 1. Core Features

- **Multi-Market Support**: Easily switch between different investment categories (currently A-shares) through a clean web interface.
- **Data Fetching and Management**:
    - Fetches historical market data from external APIs (Tushare).
    - Persists data in a local database (SQLite) to improve access speed and avoid redundant requests.
    - Supports data update mechanisms.
- **Web Interaction and Visualization**:
    - Displays a default set of core investment assets (e.g., indices, popular stocks).
    - Allows users to search and select stocks by code or name.
    - Visualizes K-line charts using ECharts with a selectable time range.
- **Backtesting Framework (Future)**: Includes a placeholder for a strategy backtesting interface, with an initial implementation of a simple "buy and hold" strategy.

## 2. Technology Stack

- **Backend**:
    - **Framework**: FastAPI
    - **Data Processing**: Pandas
    - **Database ORM**: SQLAlchemy
    - **Database**: SQLite (Development) / PostgreSQL (Production)
- **Frontend**:
    - **Framework**: React
    - **UI Component Library**: Ant Design
    - **Charting Library**: ECharts for React
    - **API Client**: Axios

## 3. Project Structure

```
ChronoRetrace/
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── api/              # API Routers
│   │   ├── core/             # Configuration
│   │   ├── db/               # Database Models & Session
│   │   ├── schemas/          # Pydantic Schemas
│   │   └── services/         # Business Logic
│   ├── .env.example          # Environment variable example
│   ├── main.py               # App entrypoint
│   └── requirements.txt
├── frontend/                 # React Frontend
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.js
│   └── package.json
├── .gitignore
└── README.md
```

## 4. Running the Application

Follow these steps to get the application running locally.

### 4.1. Prerequisites: Get a Tushare API Token

This tool uses the [Tushare Data Community](https://tushare.pro/) as its primary data source.

1.  Visit the Tushare website and register for an account.
2.  Log in and find your API Token on your personal profile page under "接口TOKEN".

### 4.2. Backend Setup

1.  **Configure Environment Variables**:
    ```bash
    cd backend
    cp .env.example .env
    ```
    Open the `.env` file and add your Tushare API Token:
    ```
    TUSHARE_API_TOKEN="YOUR_TUSHARE_TOKEN_HERE"
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Backend Server**:
    ```bash
    # From the backend directory
    uvicorn app.main:app --reload
    ```
    The server will start at `http://127.0.0.1:8000`. You can view the API documentation at `http://127.0.0.1:8000/docs`.

### 4.3. Frontend Setup

1.  **Install Dependencies**:
    ```bash
    # From the project root directory
    npm install --prefix frontend
    ```

2.  **Run the Frontend Development Server**:
    ```bash
    # From the project root directory
    npm start --prefix frontend
    ```
    The application will open automatically in your browser at `http://localhost:3000`.

## 5. Troubleshooting

### Empty Stock Dropdown

If the stock dropdown list is empty, it's likely due to one of the following issues:

1.  **Missing Tushare API Token**: The backend requires a valid Tushare API token to fetch the stock list. Make sure you have created a `.env` file in the `backend` directory and added your token to it, as described in the "Backend Setup" section.
2.  **Backend Server Not Running**: Ensure the backend server is running at `http://127.0.0.1:8000`.
3.  **Invalid Tushare API Token**: If your token is invalid or has expired, the backend will not be able to fetch data. Please verify your token on the Tushare website.