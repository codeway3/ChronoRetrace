import pytest
import pandas as pd
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime
import sys
import os
from app.db import models
from app.services import a_share_fetcher, us_stock_fetcher, db_admin, db_writer
from app.services.data_fetcher import StockDataFetcher

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# --- Test Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    models.Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        models.Base.metadata.drop_all(bind=engine)


# --- Mock Data ---
@pytest.fixture
def mock_akshare_data():
    return pd.DataFrame(
        {"代码": ["600000", "600001"], "名称": ["浦发银行", "白云机场"]}
    )


@pytest.fixture
def mock_kline_data():
    return pd.DataFrame(
        {
            "trade_date": [date(2023, 1, 1), date(2023, 1, 2)],
            "close": [10.0, 10.2],
            "high": [10.3, 10.4],
            "low": [9.9, 10.1],
            "open": [10.1, 10.1],
            "vol": [1000, 1100],
            "amount": [10000, 11220],
        }
    )


@pytest.fixture
def mock_stock_data_db():
    """Creates mock stock data to be pre-loaded into the database."""
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
            "ts_code": ["TEST.SH", "TEST.SH"],
            "interval": ["daily", "daily"],
            "close": [10.0, 10.2],
            "high": [10.3, 10.4],
            "low": [9.9, 10.1],
            "open": [10.1, 10.1],
            "vol": [1000, 1100],
            "amount": [10000, 11220],
        }
    )


@pytest.fixture
def mock_stock_data_api():
    """Creates mock stock data returned by the API."""
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2023-01-03", "2023-01-04"]),
            "close": [10.5, 10.6],
            "high": [10.7, 10.8],
            "low": [10.4, 10.5],
            "open": [10.4, 10.6],
            "vol": [1200, 1300],
            "amount": [12600, 13780],
        }
    )


# --- Helper ---
def to_date(date_str):
    if isinstance(date_str, date):
        return date_str
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def to_sql_with_date(df, table_name, con):
    """Helper to convert datetime to date before writing to SQL."""
    df_copy = df.copy()
    if "trade_date" in df_copy.columns:
        df_copy["trade_date"] = pd.to_datetime(df_copy["trade_date"]).dt.date
    df_copy.to_sql(table_name, con, if_exists="append", index=False)


# --- Tests for a_share_fetcher.py ---


@patch("app.services.a_share_fetcher.ak.fund_etf_spot_em")
@patch("app.services.a_share_fetcher.ak.stock_bj_a_spot_em")
@patch("app.services.a_share_fetcher.ak.stock_sz_a_spot_em")
@patch("app.services.a_share_fetcher.ak.stock_sh_a_spot_em")
def test_update_stock_list_from_akshare(
    mock_sh, mock_sz, mock_bj, mock_etf, db_session, mock_akshare_data
):
    """Tests updating the stock list from Akshare with proper mocking."""
    # 1. Setup: Mock the akshare functions
    mock_sh.return_value = mock_akshare_data
    mock_sz.return_value = pd.DataFrame({"代码": ["000001"], "名称": ["平安银行"]})
    mock_bj.return_value = pd.DataFrame()  # No BJ stocks for simplicity
    mock_etf.return_value = pd.DataFrame() # No ETFs for simplicity

    # 2. Action: Call the function
    a_share_fetcher.update_stock_list_from_akshare(db_session)

    # 3. Assert: Check if the data is in the database
    with db_session.connection() as conn:
        result = conn.execute(text("SELECT * FROM stock_info")).fetchall()
        assert len(result) == 3
        
        # Convert result to a set of tuples for easier comparison
        result_set = { (r[0], r[1]) for r in result }
        
        assert ("600000.SH", "浦发银行") in result_set
        assert ("600001.SH", "白云机场") in result_set
        assert ("000001.SZ", "平安银行") in result_set


# --- Tests for us_stock_fetcher.py ---


@patch("yahoo_fin.stock_info.tickers_sp500")
@patch("yahoo_fin.stock_info.tickers_nasdaq")
@patch("yahoo_fin.stock_info.tickers_dow")
@patch("yahoo_fin.stock_info.tickers_other")
def test_update_us_stock_list(
    mock_other, mock_dow, mock_nasdaq, mock_sp500, db_session
):
    """Tests updating the US stock list from yahoo_fin."""
    # 1. Setup: Mock the yahoo_fin functions
    mock_sp500.return_value = ["AAPL", "GOOG"]
    mock_nasdaq.return_value = ["MSFT", "AMZN"]
    mock_dow.return_value = ["IBM"]
    mock_other.return_value = ["V"]

    # 2. Action: Call the function
    us_stock_fetcher.update_us_stock_list(db_session)

    # 3. Assert: Check if the data is in the database
    with db_session.connection() as conn:
        result = conn.execute(text("SELECT * FROM stock_info")).fetchall()
        assert len(result) == 6
        codes = [row[0] for row in result]
        assert "AAPL" in codes
        assert "GOOG" in codes
        assert "MSFT" in codes
        assert "AMZN" in codes
        assert "IBM" in codes
        assert "V" in codes


# --- Tests for db_admin.py ---


def test_clear_all_financial_data(db_session):
    """Tests that all financial data is cleared from the database."""
    # This test needs its own session handling due to commits in the functions
    models.Base.metadata.create_all(bind=engine)

    session1 = TestingSessionLocal()
    try:
        fund_data = {"market_cap": 1e12, "pe_ratio": 25.5}
        db_writer.store_fundamental_data(session1, "MSFT", fund_data)
    finally:
        session1.close()

    session2 = TestingSessionLocal()
    try:
        actions = [
            {"action_type": "dividend", "ex_date": date(2023, 6, 1), "value": 0.5}
        ]
        db_writer.store_corporate_actions(session2, "AAPL", actions)
    finally:
        session2.close()

    session3 = TestingSessionLocal()
    try:
        earnings_data = [{"year": 2022, "net_profit": 5e10}]
        db_writer.store_annual_earnings(session3, "GOOG", earnings_data)
    finally:
        session3.close()

    # Verify data exists before clearing
    verify_session = TestingSessionLocal()
    try:
        with verify_session.connection() as conn:
            assert (
                conn.execute(text("SELECT COUNT(*) FROM fundamental_data")).scalar_one()
                == 1
            )
            assert (
                conn.execute(
                    text("SELECT COUNT(*) FROM corporate_actions")
                ).scalar_one()
                == 1
            )
            assert (
                conn.execute(text("SELECT COUNT(*) FROM annual_earnings")).scalar_one()
                == 1
            )
    finally:
        verify_session.close()

    # 2. Call the function to clear the data
    clear_session = TestingSessionLocal()
    try:
        result = db_admin.clear_all_financial_data(clear_session)
    finally:
        clear_session.close()

    # 3. Assert that the tables are empty
    final_verify_session = TestingSessionLocal()
    try:
        with final_verify_session.connection() as conn:
            assert (
                conn.execute(text("SELECT COUNT(*) FROM fundamental_data")).scalar_one()
                == 0
            )
            assert (
                conn.execute(
                    text("SELECT COUNT(*) FROM corporate_actions")
                ).scalar_one()
                == 0
            )
            assert (
                conn.execute(text("SELECT COUNT(*) FROM annual_earnings")).scalar_one()
                == 0
            )
    finally:
        final_verify_session.close()

    # 4. Assert the returned dictionary is correct
    assert result["deleted_counts"]["fundamental_data"] == 1
    assert result["deleted_counts"]["corporate_actions"] == 1
    assert result["deleted_counts"]["annual_earnings"] == 1

    models.Base.metadata.drop_all(bind=engine)


# --- Tests for db_writer.py ---


def test_store_stock_data_insert(db_session, mock_kline_data):
    """Tests inserting new stock data."""
    db_writer.store_stock_data(db_session, "TEST.SH", "daily", mock_kline_data)

    with db_session.connection() as conn:
        result = conn.execute(text("SELECT * FROM stock_data")).fetchall()
        assert len(result) == 2
        assert result[0][1] == "TEST.SH"  # ts_code
        assert to_date(result[0][2]) == date(2023, 1, 1)  # trade_date


def test_store_stock_data_upsert(db_session, mock_kline_data):
    """Tests updating existing stock data (upsert)."""
    # 1. Initial insert
    db_writer.store_stock_data(db_session, "TEST.SH", "daily", mock_kline_data)

    # 2. Create new data for upsert (updating one row, adding another)
    upsert_df = pd.DataFrame(
        {
            "trade_date": [date(2023, 1, 2), date(2023, 1, 3)],
            "close": [99.9, 10.5],  # Updated close price for 2023-01-02
            "high": [10.3, 10.6],
            "low": [9.9, 10.4],
            "open": [10.1, 10.4],
            "vol": [1100, 1200],
            "amount": [11220, 12600],
        }
    )

    # 3. Perform upsert
    db_writer.store_stock_data(db_session, "TEST.SH", "daily", upsert_df)

    # 4. Verify results
    with db_session.connection() as conn:
        result = conn.execute(
            text("SELECT * FROM stock_data ORDER BY trade_date")
        ).fetchall()
        assert len(result) == 3
        # Check updated row
        updated_row = [row for row in result if to_date(row[2]) == date(2023, 1, 2)][0]
        assert updated_row[6] == 99.9  # close price should be updated


def test_store_corporate_actions(db_session):
    """Tests storing corporate actions and ignoring duplicates."""
    actions = [
        {"action_type": "dividend", "ex_date": date(2023, 6, 1), "value": 0.5},
        {"action_type": "split", "ex_date": date(2023, 7, 1), "value": 2.0},
    ]
    db_writer.store_corporate_actions(db_session, "AAPL", actions)

    # Try to insert the same actions again
    db_writer.store_corporate_actions(db_session, "AAPL", actions)

    with db_session.connection() as conn:
        result = conn.execute(text("SELECT * FROM corporate_actions")).fetchall()
        assert len(result) == 2


def test_store_fundamental_data(db_session):
    """Tests inserting and updating fundamental data."""
    fund_data = {"market_cap": 1e12, "pe_ratio": 25.5}
    db_writer.store_fundamental_data(db_session, "MSFT", fund_data)

    with db_session.connection() as conn:
        result = conn.execute(text("SELECT * FROM fundamental_data")).fetchone()
        assert result[1] == "MSFT"
        assert result[2] == 1e12

    # Update the data
    updated_fund_data = {"market_cap": 1.1e12, "pe_ratio": 26.0}

    # Use a new session for the update to avoid ResourceClosedError
    new_session = TestingSessionLocal()
    try:
        db_writer.store_fundamental_data(new_session, "MSFT", updated_fund_data)
        with new_session.connection() as conn:
            result_updated = conn.execute(
                text("SELECT * FROM fundamental_data")
            ).fetchone()
            assert result_updated[2] == 1.1e12
    finally:
        new_session.close()


def test_store_annual_earnings(db_session):
    """Tests inserting and updating annual earnings data."""
    earnings_data = [
        {"year": 2022, "net_profit": 5e10},
        {"year": 2023, "net_profit": 5.5e10},
    ]
    db_writer.store_annual_earnings(db_session, "GOOG", earnings_data)

    # Update data for 2023 and add 2024
    updated_earnings = [
        {"year": 2023, "net_profit": 5.6e10},
        {"year": 2024, "net_profit": 6.0e10},
    ]

    new_session = TestingSessionLocal()
    try:
        db_writer.store_annual_earnings(new_session, "GOOG", updated_earnings)
        with new_session.connection() as conn:
            result = conn.execute(
                text("SELECT * FROM annual_earnings ORDER BY year")
            ).fetchall()
            assert len(result) == 3
            assert result[1][3] == 5.6e10  # 2023 data updated
    finally:
        new_session.close()


# --- Tests for StockDataFetcher ---


def test_fetch_from_db(db_session, mock_stock_data_db):
    """Tests that data is correctly fetched from the database."""
    # 1. Setup: Pre-load data into the test database
    to_sql_with_date(mock_stock_data_db, "stock_data", db_session.bind)

    # 2. Action: Instantiate fetcher and call the method
    fetcher = StockDataFetcher(
        db=db_session, stock_code="TEST.SH", interval="daily", market_type="A_share"
    )
    fetcher.start_date = date(2023, 1, 1)
    fetcher.end_date = date(2023, 1, 2)

    df = fetcher._fetch_from_db()

    # 3. Assert: Check if the DataFrame is correct
    assert not df.empty
    assert len(df) == 2
    assert "id" not in df.columns
    assert df["ts_code"].iloc[0] == "TEST.SH"
    assert pd.to_datetime(df["trade_date"]).iloc[0].date() == date(2023, 1, 1)


@patch("app.services.a_share_fetcher.fetch_a_share_data_from_akshare")
def test_fetch_from_api_when_db_empty(
    mock_fetch_a_share, db_session, mock_stock_data_api
):
    """Tests that the API is called when the database is empty."""
    # 1. Setup: Mock the API fetcher
    mock_fetch_a_share.return_value = mock_stock_data_api

    # 2. Action: Instantiate fetcher and call the main fetch method
    fetcher = StockDataFetcher(
        db=db_session, stock_code="TEST.SH", interval="daily", market_type="A_share"
    )
    df = fetcher.fetch_stock_data()

    # 3. Assert: Check API call and returned data
    mock_fetch_a_share.assert_called_once()
    assert not df.empty
    assert len(df) == 2
    assert df["close"].iloc[0] == 10.5

    # 4. Assert: Check if data was stored in the DB
    db_df = pd.read_sql(
        text("SELECT * FROM stock_data WHERE ts_code='TEST.SH'"),
        db_session.connection(),
    )
    assert not db_df.empty
    assert len(db_df) == 2


def test_fetch_from_db_when_data_is_fresh(db_session, mock_stock_data_db):
    """Tests that fresh data from the DB is returned without calling the API."""
    # 1. Setup: Load fresh data into the DB
    fresh_data = mock_stock_data_db.copy()
    fresh_data["trade_date"] = [
        (datetime.now() - pd.Timedelta(days=2)).date(),
        (datetime.now() - pd.Timedelta(days=1)).date(),
    ]
    to_sql_with_date(fresh_data, "stock_data", db_session.bind)

    # 2. Action
    with patch(
        "app.services.a_share_fetcher.fetch_a_share_data_from_akshare"
    ) as mock_fetch:
        fetcher = StockDataFetcher(
            db=db_session, stock_code="TEST.SH", interval="daily", market_type="A_share"
        )
        df = fetcher.fetch_stock_data()

        # 3. Assert
        mock_fetch.assert_not_called()  # API should not be called
        assert not df.empty
        assert len(df) == 2
        assert df["ts_code"].iloc[0] == "TEST.SH"


@patch("app.services.a_share_fetcher.fetch_a_share_data_from_akshare")
def test_fetch_from_api_when_db_stale(
    mock_fetch_a_share, db_session, mock_stock_data_db, mock_stock_data_api
):
    """Tests that the API is called when DB data is stale."""
    # 1. Setup: Load old data into the DB
    to_sql_with_date(mock_stock_data_db, "stock_data", db_session.bind)
    mock_fetch_a_share.return_value = mock_stock_data_api

    # 2. Action
    fetcher = StockDataFetcher(
        db=db_session, stock_code="TEST.SH", interval="daily", market_type="A_share"
    )
    df = fetcher.fetch_stock_data()

    # 3. Assert
    mock_fetch_a_share.assert_called_once()
    assert not df.empty
    assert len(df) == 2  # Should return the new data from API
    assert df["close"].iloc[0] == 10.5


@patch("app.services.us_stock_fetcher.fetch_from_yfinance")
def test_fetch_us_stock_directly_from_api(
    mock_fetch_us, db_session, mock_stock_data_api
):
    """Tests that US stock data is fetched from the correct (yfinance) API."""
    # 1. Setup
    mock_fetch_us.return_value = mock_stock_data_api

    # 2. Action
    fetcher = StockDataFetcher(
        db=db_session, stock_code="AAPL", interval="daily", market_type="US_stock"
    )
    df = fetcher.fetch_stock_data()

    # 3. Assert
    mock_fetch_us.assert_called_once()
    assert not df.empty
    assert len(df) == 2


@patch("app.services.a_share_fetcher.fetch_a_share_data_from_akshare")
def test_fetch_minute_data_bypasses_db(
    mock_fetch_a_share, db_session, mock_stock_data_api
):
    """Tests that fetching 'minute' interval data bypasses the DB cache."""
    # 1. Setup
    mock_fetch_a_share.return_value = mock_stock_data_api

    # 2. Action
    with patch.object(StockDataFetcher, "_fetch_from_db") as mock_fetch_db:
        fetcher = StockDataFetcher(
            db=db_session,
            stock_code="TEST.SH",
            interval="minute",
            market_type="A_share",
        )
        df = fetcher.fetch_stock_data()

        # 3. Assert
        mock_fetch_db.assert_not_called()
        mock_fetch_a_share.assert_called_once()
        assert not df.empty
        assert len(df) == 2
