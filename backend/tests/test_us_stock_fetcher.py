from unittest.mock import Mock, patch

import pandas as pd

from app.services.us_stock_fetcher import (_convert_ts_code_to_yfinance,
                                           fetch_from_yfinance,
                                           update_us_stock_list)


class TestConvertTsCodeToYfinance:
    """Test ts_code to yfinance conversion."""

    def test_convert_sh_suffix(self):
        """Test conversion of SH suffix."""
        result = _convert_ts_code_to_yfinance("AAPL.SH")
        assert result == "AAPL.SS"

    def test_convert_no_suffix(self):
        """Test conversion of code without suffix."""
        result = _convert_ts_code_to_yfinance("AAPL")
        assert result == "AAPL"

    def test_convert_sz_suffix(self):
        """Test conversion of SZ suffix."""
        result = _convert_ts_code_to_yfinance("AAPL.SZ")
        assert result == "AAPL.SZ"  # SZ suffix unchanged


class TestFetchFromYfinance:
    """Test yfinance data fetching."""

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_success(self, mock_download):
        """Test successful data fetching from yfinance."""
        # Mock yfinance response
        mock_data = pd.DataFrame(
            {
                "Date": pd.date_range("2023-01-01", periods=5),
                "Open": [150.0, 151.0, 152.0, 153.0, 154.0],
                "High": [155.0, 156.0, 157.0, 158.0, 159.0],
                "Low": [145.0, 146.0, 147.0, 148.0, 149.0],
                "Close": [152.0, 153.0, 154.0, 155.0, 156.0],
                "Volume": [1000, 1100, 1200, 1300, 1400],
                "Adj Close": [151.0, 152.0, 153.0, 154.0, 155.0],
            }
        )
        mock_download.return_value = mock_data

        result = fetch_from_yfinance("AAPL", "2023-01-01", "2023-01-05")

        assert not result.empty
        assert len(result) == 5
        assert "trade_date" in result.columns
        assert "open" in result.columns
        assert "high" in result.columns
        assert "low" in result.columns
        assert "close" in result.columns
        assert "vol" in result.columns
        # Note: adj_close is not in final output, only in intermediate processing
        assert "pre_close" in result.columns
        assert "change" in result.columns
        assert "pct_chg" in result.columns
        assert "amount" in result.columns

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_empty_response(self, mock_download):
        """Test handling of empty response from yfinance."""
        mock_download.return_value = pd.DataFrame()

        result = fetch_from_yfinance("UNKNOWN", "2023-01-01", "2023-01-05")

        assert result.empty

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_multiindex_columns(self, mock_download):
        """Test handling of MultiIndex columns from yfinance."""
        mock_data = pd.DataFrame(
            {
                "Date": pd.date_range("2023-01-01", periods=3),
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [145.0, 146.0, 147.0],
                "Close": [152.0, 153.0, 154.0],
                "Volume": [1000, 1100, 1200],
                "Adj Close": [151.0, 152.0, 153.0],
            }
        )
        # Create MultiIndex columns
        mock_data.columns = pd.MultiIndex.from_tuples(
            [
                ("Date", ""),
                ("Open", ""),
                ("High", ""),
                ("Low", ""),
                ("Close", ""),
                ("Volume", ""),
                ("Adj Close", ""),
            ]
        )
        mock_download.return_value = mock_data

        result = fetch_from_yfinance("AAPL", "2023-01-01", "2023-01-03")

        assert not result.empty
        assert "trade_date" in result.columns
        assert "open" in result.columns

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_weekly_interval(self, mock_download):
        """Test weekly interval handling."""
        mock_data = pd.DataFrame(
            {
                "Date": pd.date_range("2023-01-01", periods=3, freq="W"),
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [145.0, 146.0, 147.0],
                "Close": [152.0, 153.0, 154.0],
                "Volume": [1000, 1100, 1200],
                "Adj Close": [151.0, 152.0, 153.0],
            }
        )
        mock_download.return_value = mock_data

        result = fetch_from_yfinance("AAPL", "2023-01-01", "2023-01-21", "weekly")

        assert not result.empty
        # Verify that yfinance was called with correct interval
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        assert call_args[1]["interval"] == "1wk"

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_monthly_interval(self, mock_download):
        """Test monthly interval handling."""
        mock_data = pd.DataFrame(
            {
                "Date": pd.date_range("2023-01-01", periods=3, freq="ME"),
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [145.0, 146.0, 147.0],
                "Close": [152.0, 153.0, 154.0],
                "Volume": [1000, 1100, 1200],
                "Adj Close": [151.0, 152.0, 153.0],
            }
        )
        mock_download.return_value = mock_data

        result = fetch_from_yfinance("AAPL", "2023-01-01", "2023-03-31", "monthly")

        assert not result.empty
        # Verify that yfinance was called with correct interval
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        assert call_args[1]["interval"] == "1mo"

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_invalid_interval(self, mock_download):
        """Test handling of invalid interval."""
        mock_data = pd.DataFrame(
            {
                "Date": pd.date_range("2023-01-01", periods=3),
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [145.0, 146.0, 147.0],
                "Close": [152.0, 153.0, 154.0],
                "Volume": [1000, 1100, 1200],
                "Adj Close": [151.0, 152.0, 153.0],
            }
        )
        mock_download.return_value = mock_data

        result = fetch_from_yfinance("AAPL", "2023-01-01", "2023-01-03", "invalid")

        assert not result.empty
        # Should default to '1d' interval
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        assert call_args[1]["interval"] == "1d"

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_missing_adj_close(self, mock_download):
        """Test handling of missing Adj Close column."""
        mock_data = pd.DataFrame(
            {
                "Date": pd.date_range("2023-01-01", periods=3),
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [145.0, 146.0, 147.0],
                "Close": [152.0, 153.0, 154.0],
                "Volume": [1000, 1100, 1200],
                # Missing Adj Close column
            }
        )
        mock_download.return_value = mock_data

        result = fetch_from_yfinance("AAPL", "2023-01-01", "2023-01-03")

        assert not result.empty
        # Should handle missing adj_close gracefully by not including it in final output
        assert "adj_close" not in result.columns
        assert "pre_close" in result.columns
        assert "change" in result.columns

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_nan_dates_handling(self, mock_download):
        """Test handling of NaN dates in response."""
        mock_data = pd.DataFrame(
            {
                "Date": [
                    pd.Timestamp("2023-01-01"),
                    pd.NaT,
                    pd.Timestamp("2023-01-03"),
                ],
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [145.0, 146.0, 147.0],
                "Close": [152.0, 153.0, 154.0],
                "Volume": [1000, 1100, 1200],
                "Adj Close": [151.0, 152.0, 153.0],
            }
        )
        mock_download.return_value = mock_data

        result = fetch_from_yfinance("AAPL", "2023-01-01", "2023-01-03")

        # Should drop rows with NaN dates
        assert len(result) == 2  # Only 2 valid dates
        assert "trade_date" in result.columns

    @patch("app.services.us_stock_fetcher.yf.download")
    def test_fetch_from_yfinance_symbol_conversion(self, mock_download):
        """Test that ts_code is properly converted to yfinance format."""
        mock_data = pd.DataFrame(
            {
                "Date": pd.date_range("2023-01-01", periods=3),
                "Open": [150.0, 151.0, 152.0],
                "High": [155.0, 156.0, 157.0],
                "Low": [145.0, 146.0, 147.0],
                "Close": [152.0, 153.0, 154.0],
                "Volume": [1000, 1100, 1200],
                "Adj Close": [151.0, 152.0, 153.0],
            }
        )
        mock_download.return_value = mock_data

        # Test with SH suffix
        result = fetch_from_yfinance("AAPL.SH", "2023-01-01", "2023-01-03")
        assert not result.empty

        # Verify that yfinance was called with converted symbol
        mock_download.assert_called_once()
        call_args = mock_download.call_args
        # Should be converted from .SH to .SS
        assert call_args[0][0] == "AAPL.SS"


class TestUpdateUsStockList:
    """Test US stock list update."""

    @patch("app.services.us_stock_fetcher.si.tickers_sp500")
    @patch("app.services.us_stock_fetcher.si.tickers_nasdaq")
    @patch("app.services.us_stock_fetcher.si.tickers_dow")
    @patch("app.services.us_stock_fetcher.si.tickers_other")
    @patch("app.services.us_stock_fetcher.sqlite_insert")
    def test_update_us_stock_list_success(
        self, mock_insert, mock_other, mock_dow, mock_nasdaq, mock_sp500
    ):
        """Test successful US stock list update."""
        # Mock S&P 500 data
        mock_sp500.return_value = ["AAPL", "MSFT", "GOOGL"]

        # Mock NASDAQ data
        mock_nasdaq.return_value = ["AAPL", "MSFT", "GOOGL", "TSLA"]

        # Mock Dow Jones data
        mock_dow.return_value = ["AAPL", "MSFT", "GOOGL", "JPM"]

        # Mock other exchanges data
        mock_other.return_value = ["BRK.A", "BRK.B"]

        # Mock database insert
        mock_stmt = Mock()
        mock_insert.return_value = mock_stmt
        mock_stmt.on_conflict_do_update.return_value = mock_stmt

        # Mock database session
        mock_db = Mock()

        update_us_stock_list(mock_db)

        # Verify that all exchanges were processed
        mock_sp500.assert_called_once()
        mock_nasdaq.assert_called_once()
        mock_other.assert_called_once()

    @patch("app.services.us_stock_fetcher.si.tickers_sp500")
    @patch("app.services.us_stock_fetcher.si.tickers_nasdaq")
    @patch("app.services.us_stock_fetcher.si.tickers_dow")
    @patch("app.services.us_stock_fetcher.si.tickers_other")
    def test_update_us_stock_list_sp500_failure(
        self, mock_other, mock_dow, mock_nasdaq, mock_sp500
    ):
        """Test US stock list update with S&P 500 failure."""
        # Mock S&P 500 failure
        mock_sp500.side_effect = Exception("S&P 500 error")

        # Mock NASDAQ success
        mock_nasdaq.return_value = ["AAPL", "MSFT", "GOOGL"]

        # Mock Dow Jones success
        mock_dow.return_value = ["AAPL", "MSFT", "GOOGL", "JPM"]

        # Mock other exchanges success
        mock_other.return_value = ["BRK.A", "BRK.B"]

        mock_db = Mock()

        update_us_stock_list(mock_db)

        # Current implementation stops on first exception, so only S&P 500 should be called
        mock_sp500.assert_called_once()
        mock_nasdaq.assert_not_called()
        mock_other.assert_not_called()

    @patch("app.services.us_stock_fetcher.si.tickers_sp500")
    @patch("app.services.us_stock_fetcher.si.tickers_nasdaq")
    @patch("app.services.us_stock_fetcher.si.tickers_dow")
    @patch("app.services.us_stock_fetcher.si.tickers_other")
    def test_update_us_stock_list_all_failures(
        self, mock_other, mock_dow, mock_nasdaq, mock_sp500
    ):
        """Test US stock list update when all exchanges fail."""
        # Mock all exchanges failing
        mock_sp500.side_effect = Exception("S&P 500 error")
        mock_nasdaq.side_effect = Exception("NASDAQ error")
        mock_dow.side_effect = Exception("Dow Jones error")
        mock_other.side_effect = Exception("Other exchanges error")

        mock_db = Mock()

        update_us_stock_list(mock_db)

        # Current implementation stops on first exception, so only S&P 500 should be called
        mock_sp500.assert_called_once()
        mock_nasdaq.assert_not_called()
        mock_other.assert_not_called()

    @patch("app.services.us_stock_fetcher.si.tickers_sp500")
    @patch("app.services.us_stock_fetcher.si.tickers_nasdaq")
    @patch("app.services.us_stock_fetcher.si.tickers_dow")
    @patch("app.services.us_stock_fetcher.si.tickers_other")
    def test_update_us_stock_list_empty_lists(
        self, mock_other, mock_dow, mock_nasdaq, mock_sp500
    ):
        """Test US stock list update with empty lists."""
        # Mock empty lists
        mock_sp500.return_value = []
        mock_nasdaq.return_value = []
        mock_dow.return_value = []
        mock_other.return_value = []

        mock_db = Mock()

        update_us_stock_list(mock_db)

        # Should handle empty lists gracefully
        mock_sp500.assert_called_once()
        mock_nasdaq.assert_called_once()
        mock_other.assert_called_once()

    @patch("app.services.us_stock_fetcher.si.tickers_sp500")
    @patch("app.services.us_stock_fetcher.si.tickers_nasdaq")
    @patch("app.services.us_stock_fetcher.si.tickers_dow")
    @patch("app.services.us_stock_fetcher.si.tickers_other")
    def test_update_us_stock_list_duplicate_symbols(
        self, mock_other, mock_dow, mock_nasdaq, mock_sp500
    ):
        """Test US stock list update with duplicate symbols across exchanges."""
        # Mock overlapping symbols
        mock_sp500.return_value = ["AAPL", "MSFT", "GOOGL"]
        mock_nasdaq.return_value = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "TSLA",
        ]  # Overlapping with S&P 500
        mock_dow.return_value = ["AAPL", "MSFT", "GOOGL", "JPM"]  # Also overlapping
        mock_other.return_value = ["BRK.A", "BRK.B", "AAPL"]  # Also overlapping

        mock_db = Mock()

        update_us_stock_list(mock_db)

        # Should handle duplicates gracefully
        mock_sp500.assert_called_once()
        mock_nasdaq.assert_called_once()
        mock_other.assert_called_once()
