from unittest.mock import Mock, patch

import pytest

from app.services.data_fetcher import (force_update_stock_list,
                                       get_all_stocks_list)


class TestGetAllStocksList:
    """Test stock list retrieval functions."""

    def test_get_all_stocks_list_a_share_empty_cache(self):
        """Test getting A-share stock list when cache is empty."""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        with patch(
            "app.services.data_fetcher.a_share_fetcher.update_stock_list_from_akshare"
        ) as mock_update:
            get_all_stocks_list(mock_db, "A_share")

            mock_update.assert_called_once_with(mock_db)
            mock_query.all.assert_called_once()

    def test_get_all_stocks_list_a_share_with_cache(self):
        """Test getting A-share stock list when cache exists."""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 100  # Cache has data

        get_all_stocks_list(mock_db, "A_share")

        # Should not call update function when cache exists
        mock_query.all.assert_called_once()

    def test_get_all_stocks_list_us_stock_empty_cache(self):
        """Test getting US stock list when cache is empty."""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        with patch(
            "app.services.data_fetcher.us_stock_fetcher.update_us_stock_list"
        ) as mock_update:
            get_all_stocks_list(mock_db, "US_stock")

            mock_update.assert_called_once_with(mock_db)
            mock_query.all.assert_called_once()

    def test_get_all_stocks_list_unknown_market(self):
        """Test getting stock list for unknown market type."""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        get_all_stocks_list(mock_db, "unknown_market")

        # Should not call any update function for unknown market
        mock_query.all.assert_called_once()

    def test_get_all_stocks_list_update_failure(self):
        """Test handling of update failure."""
        mock_db = Mock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        with patch(
            "app.services.data_fetcher.a_share_fetcher.update_stock_list_from_akshare"
        ) as mock_update:
            mock_update.side_effect = Exception("Update failed")

            get_all_stocks_list(mock_db, "A_share")

            # Should continue even if update fails
            mock_query.all.assert_called_once()


class TestForceUpdateStockList:
    """Test forced stock list update functions."""

    def test_force_update_stock_list_a_share_success(self):
        """Test successful forced update of A-share stock list."""
        mock_db = Mock()

        with patch(
            "app.services.data_fetcher.a_share_fetcher.update_stock_list_from_akshare"
        ) as mock_update:
            force_update_stock_list(mock_db, "A_share")

            mock_update.assert_called_once_with(mock_db)

    def test_force_update_stock_list_us_stock_success(self):
        """Test successful forced update of US stock list."""
        mock_db = Mock()

        with patch(
            "app.services.data_fetcher.us_stock_fetcher.update_us_stock_list"
        ) as mock_update:
            force_update_stock_list(mock_db, "US_stock")

            mock_update.assert_called_once_with(mock_db)

    def test_force_update_stock_list_unknown_market(self):
        """Test forced update for unknown market type."""
        mock_db = Mock()

        # Current implementation doesn't raise exception for unknown market types
        # It just logs and continues without doing anything
        force_update_stock_list(mock_db, "unknown_market")

        # Should not raise an exception, just log a warning
        # This test verifies the current behavior

    def test_force_update_stock_list_a_share_failure(self):
        """Test handling of A-share update failure."""
        mock_db = Mock()

        with patch(
            "app.services.data_fetcher.a_share_fetcher.update_stock_list_from_akshare"
        ) as mock_update:
            mock_update.side_effect = Exception("Update failed")

            with pytest.raises(Exception, match="Update failed"):
                force_update_stock_list(mock_db, "A_share")

    def test_force_update_stock_list_us_stock_failure(self):
        """Test handling of US stock update failure."""
        mock_db = Mock()

        with patch(
            "app.services.data_fetcher.us_stock_fetcher.update_us_stock_list"
        ) as mock_update:
            mock_update.side_effect = Exception("Update failed")

            with pytest.raises(Exception, match="Update failed"):
                force_update_stock_list(mock_db, "US_stock")
