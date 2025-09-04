from unittest.mock import Mock, patch

import pandas as pd
import pytest

from app.services.a_share_fetcher import (
    _baostock_query_with_retry, baostock_session,
    fetch_annual_net_profit_from_baostock, update_stock_list_from_akshare)


class TestBaostockSession:
    """Test baostock session management."""

    @patch("app.services.a_share_fetcher.bs.login")
    @patch("app.services.a_share_fetcher.bs.logout")
    def test_baostock_session_success(self, mock_logout, mock_login):
        """Test successful baostock session."""
        mock_result = Mock()
        mock_result.error_code = "0"
        mock_login.return_value = mock_result

        with baostock_session():
            pass

        mock_login.assert_called_once()
        mock_logout.assert_called_once()

    @patch("app.services.a_share_fetcher.bs.login")
    @patch("app.services.a_share_fetcher.bs.logout")
    def test_baostock_session_login_failure(self, mock_logout, mock_login):
        """Test baostock session with login failure."""
        mock_result = Mock()
        mock_result.error_code = "1"
        mock_result.error_msg = "Login failed"
        mock_login.return_value = mock_result

        with pytest.raises(RuntimeError, match="Baostock login failed: Login failed"):
            with baostock_session():
                pass

        mock_login.assert_called_once()
        mock_logout.assert_not_called()


class TestBaostockQueryWithRetry:
    """Test baostock query retry logic."""

    def test_baostock_query_success_first_attempt(self):
        """Test successful query on first attempt."""
        mock_query_func = Mock()
        mock_result = Mock()
        mock_result.error_code = "0"
        mock_result.data = [["2023", "1000000"]]
        mock_result.fields = ["year", "netProfit"]
        mock_result.get_data.return_value = pd.DataFrame(
            [["2023", "1000000"]], columns=["year", "netProfit"]
        )
        mock_query_func.return_value = mock_result

        result = _baostock_query_with_retry(mock_query_func, "test_code")

        assert result is not None
        assert not result.empty
        mock_query_func.assert_called_once()

    def test_baostock_query_network_error_retry(self):
        """Test query with network error and retry."""
        mock_query_func = Mock()
        mock_result = Mock()
        mock_result.error_code = "10002007"  # Network reception error
        mock_result.error_msg = "Network error"
        mock_query_func.return_value = mock_result

        result = _baostock_query_with_retry(mock_query_func, "test_code")

        assert result is None
        # Should have retried twice
        assert mock_query_func.call_count == 2

    def test_baostock_query_data_mismatch_handling(self):
        """Test handling of data/field mismatch."""
        mock_query_func = Mock()
        mock_query_func.__name__ = "mock_query_func"  # Fix __name__ attribute
        mock_result = Mock()
        mock_result.error_code = "0"
        mock_result.data = [["2023", "1000000"]]  # 2 columns
        mock_result.fields = ["year", "netProfit", "extra_field"]  # 3 fields
        mock_result.get_data.side_effect = ValueError("columns passed")
        mock_query_func.return_value = mock_result

        result = _baostock_query_with_retry(mock_query_func, "test_code")

        assert result is not None
        # Should use only available data columns
        assert len(result.columns) == 2

    def test_baostock_query_empty_data(self):
        """Test handling of empty data."""
        mock_query_func = Mock()
        mock_result = Mock()
        mock_result.error_code = "0"
        mock_result.data = []
        mock_result.get_data.return_value = pd.DataFrame()
        mock_query_func.return_value = mock_result

        result = _baostock_query_with_retry(mock_query_func, "test_code")

        assert result is not None
        assert result.empty

    def test_baostock_query_circuit_breaker(self):
        """Test circuit breaker after multiple consecutive failures."""
        mock_query_func = Mock()
        mock_result = Mock()
        mock_result.error_code = "10002007"  # Network error
        mock_query_func.return_value = mock_result

        # Mock time.sleep to speed up test
        with patch("app.services.a_share_fetcher.time.sleep"):
            result = _baostock_query_with_retry(mock_query_func, "test_code")

        assert result is None
        # Should stop after max_retries attempts (2 attempts: attempt=0, attempt=1)
        assert mock_query_func.call_count == 2


class TestFetchAnnualNetProfit:
    """Test annual net profit fetching."""

    @patch("app.services.a_share_fetcher.baostock_session")
    @patch("app.services.a_share_fetcher._baostock_query_with_retry")
    def test_fetch_annual_net_profit_success(self, mock_query, mock_session):
        """Test successful annual net profit fetching."""
        mock_session.return_value.__enter__ = Mock()
        mock_session.return_value.__exit__ = Mock()

        # Mock quarterly data
        mock_quarter_data = pd.DataFrame([["1000000"]], columns=["netProfit"])
        mock_query.return_value = mock_quarter_data

        result = fetch_annual_net_profit_from_baostock("000001.SH", years=2)

        assert len(result) > 0
        assert all("year" in item for item in result)
        assert all("net_profit" in item for item in result)

    @patch("app.services.a_share_fetcher.baostock_session")
    @patch("app.services.a_share_fetcher._baostock_query_with_retry")
    def test_fetch_annual_net_profit_no_data(self, mock_query, mock_session):
        """Test annual net profit fetching with no data."""
        mock_session.return_value.__enter__ = Mock()
        mock_session.return_value.__exit__ = Mock()

        mock_query.return_value = None

        result = fetch_annual_net_profit_from_baostock("000001.SH", years=2)

        assert result == []

    @patch("app.services.a_share_fetcher.baostock_session")
    @patch("app.services.a_share_fetcher._baostock_query_with_retry")
    def test_fetch_annual_net_profit_invalid_profit_value(
        self, mock_query, mock_session
    ):
        """Test handling of invalid profit values."""
        mock_session.return_value.__enter__ = Mock()
        mock_session.return_value.__exit__ = Mock()

        # Mock data with invalid profit value
        mock_quarter_data = pd.DataFrame([["invalid"]], columns=["netProfit"])
        mock_query.return_value = mock_quarter_data

        result = fetch_annual_net_profit_from_baostock("000001.SH", years=1)

        # Should handle invalid values gracefully
        assert isinstance(result, list)

    @patch("app.services.a_share_fetcher.baostock_session")
    @patch("app.services.a_share_fetcher._baostock_query_with_retry")
    def test_fetch_annual_net_profit_symbol_conversion(self, mock_query, mock_session):
        """Test symbol conversion for baostock."""
        mock_session.return_value.__enter__ = Mock()
        mock_session.return_value.__exit__ = Mock()

        mock_query.return_value = pd.DataFrame([["1000000"]], columns=["netProfit"])

        # Test SH suffix conversion
        result = fetch_annual_net_profit_from_baostock("000001.SH", years=1)
        assert result is not None

        # Test SZ suffix conversion
        result = fetch_annual_net_profit_from_baostock("000001.SZ", years=1)
        assert result is not None


class TestUpdateStockListFromAkshare:
    """Test stock list update from akshare."""

    @patch("app.services.a_share_fetcher.ak.stock_sh_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.stock_sz_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.fund_etf_spot_em")
    @patch("app.services.a_share_fetcher.sqlite_insert")
    def test_update_stock_list_success(self, mock_insert, mock_etf, mock_sz, mock_sh):
        """Test successful stock list update."""
        # Mock SH market data
        mock_sh.return_value = pd.DataFrame(
            {"代码": ["000001", "000002"], "名称": ["平安银行", "万科A"]}
        )

        # Mock SZ market data
        mock_sz.return_value = pd.DataFrame(
            {"代码": ["000001", "000002"], "名称": ["平安银行", "万科A"]}
        )

        # Mock ETF data
        mock_etf.return_value = pd.DataFrame(
            {"代码": ["510050", "159919"], "名称": ["50ETF", "300ETF"]}
        )

        # Mock database insert
        mock_stmt = Mock()
        mock_insert.return_value = mock_stmt
        mock_stmt.on_conflict_do_update.return_value = mock_stmt

        # Mock database session
        mock_db = Mock()

        update_stock_list_from_akshare(mock_db)

        # Verify that all markets were processed
        mock_sh.assert_called_once()
        mock_sz.assert_called_once()
        mock_etf.assert_called_once()

    @patch("app.services.a_share_fetcher.ak.stock_sh_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.stock_sz_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.fund_etf_spot_em")
    def test_update_stock_list_market_failure(self, mock_etf, mock_sz, mock_sh):
        """Test stock list update with market failure."""
        # Mock SH market failure
        mock_sh.side_effect = Exception("SH market error")

        # Mock SZ market success
        mock_sz.return_value = pd.DataFrame({"代码": ["000001"], "名称": ["平安银行"]})

        # Mock ETF success
        mock_etf.return_value = pd.DataFrame({"代码": ["510050"], "名称": ["50ETF"]})

        mock_db = Mock()

        update_stock_list_from_akshare(mock_db)

        # Should continue processing other markets even if one fails
        mock_sz.assert_called_once()
        mock_etf.assert_called_once()

    @patch("app.services.a_share_fetcher.ak.stock_sh_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.stock_sz_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.fund_etf_spot_em")
    def test_update_stock_list_column_fallback(self, mock_etf, mock_sz, mock_sh):
        """Test stock list update with column name fallback."""
        # Mock SH market with different column names
        mock_sh.return_value = pd.DataFrame({"code": ["000001"], "name": ["平安银行"]})

        # Mock SZ market with standard column names
        mock_sz.return_value = pd.DataFrame({"代码": ["000001"], "名称": ["平安银行"]})

        # Mock ETF data
        mock_etf.return_value = pd.DataFrame({"代码": ["510050"], "名称": ["50ETF"]})

        mock_db = Mock()

        update_stock_list_from_akshare(mock_db)

        # Should handle different column names gracefully
        mock_sh.assert_called_once()
        mock_sz.assert_called_once()
        mock_etf.assert_called_once()

    @patch("app.services.a_share_fetcher.ak.stock_sh_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.stock_sz_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.fund_etf_spot_em")
    def test_update_stock_list_etf_suffix_detection(self, mock_etf, mock_sz, mock_sh):
        """Test ETF market suffix detection."""
        # Mock empty stock markets
        mock_sh.return_value = pd.DataFrame()
        mock_sz.return_value = pd.DataFrame()

        # Mock ETF data with different prefixes
        mock_etf.return_value = pd.DataFrame(
            {
                "代码": ["510050", "159919", "588000"],
                "名称": ["50ETF", "300ETF", "科创50ETF"],
            }
        )

        mock_db = Mock()

        update_stock_list_from_akshare(mock_db)

        # Should detect market suffixes correctly
        mock_etf.assert_called_once()

    @patch("app.services.a_share_fetcher.ak.stock_sh_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.stock_sz_a_spot_em")
    @patch("app.services.a_share_fetcher.ak.fund_etf_spot_em")
    def test_update_stock_list_all_markets_fail(self, mock_etf, mock_sz, mock_sh):
        """Test stock list update when all markets fail."""
        # Mock all markets failing
        mock_sh.side_effect = Exception("SH market error")
        mock_sz.side_effect = Exception("SZ market error")
        mock_etf.side_effect = Exception("ETF market error")

        mock_db = Mock()

        update_stock_list_from_akshare(mock_db)

        # Should handle all failures gracefully
        mock_sh.assert_called_once()
        mock_sz.assert_called_once()
        mock_etf.assert_called_once()
