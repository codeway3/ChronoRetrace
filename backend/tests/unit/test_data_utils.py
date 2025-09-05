import numpy as np
import pandas as pd

from app.data.managers.data_utils import calculate_ma


def test_calculate_ma_with_sufficient_data():
    """Test MA calculation when there is enough data for all periods."""
    # Create DataFrame with 100 rows (enough for MA60)
    data = {
        "close": [i for i in range(1, 101)]  # 1 to 100
    }
    df = pd.DataFrame(data)

    result = calculate_ma(df)

    # Check that all MA columns are present
    assert "ma5" in result.columns
    assert "ma10" in result.columns
    assert "ma20" in result.columns
    assert "ma60" in result.columns

    # Check that MAs are calculated correctly
    # MA5 of last row should be average of last 5 values (96, 97, 98, 99, 100)
    expected_ma5 = (96 + 97 + 98 + 99 + 100) / 5
    assert abs(result["ma5"].iloc[-1] - expected_ma5) < 0.001

    # MA60 of last row should be average of last 60 values (41 to 100)
    expected_ma60 = sum(range(41, 101)) / 60
    assert abs(result["ma60"].iloc[-1] - expected_ma60) < 0.001


def test_calculate_ma_with_insufficient_data():
    """Test MA calculation when there is not enough data for longer periods."""
    # Create DataFrame with only 10 rows (enough for MA5 and MA10, but not MA20 or MA60)
    data = {
        "close": [i for i in range(1, 11)]  # 1 to 10
    }
    df = pd.DataFrame(data)

    result = calculate_ma(df)

    # Check that all MA columns are present
    assert "ma5" in result.columns
    assert "ma10" in result.columns
    assert "ma20" in result.columns
    assert "ma60" in result.columns

    # Check that shorter MAs are calculated
    assert result["ma5"].iloc[-1] is not None
    assert result["ma10"].iloc[-1] is not None

    # Check that longer MAs are None (insufficient data)
    assert result["ma20"].iloc[-1] is None
    assert result["ma60"].iloc[-1] is None


def test_calculate_ma_with_minimal_data():
    """Test MA calculation with minimal data (less than shortest MA period)."""
    # Create DataFrame with only 3 rows (less than MA5)
    data = {"close": [1, 2, 3]}
    df = pd.DataFrame(data)

    result = calculate_ma(df)

    # Check that all MA columns are present but None
    assert "ma5" in result.columns
    assert "ma10" in result.columns
    assert "ma20" in result.columns
    assert "ma60" in result.columns

    # All MAs should be None
    assert result["ma5"].iloc[-1] is None
    assert result["ma10"].iloc[-1] is None
    assert result["ma20"].iloc[-1] is None
    assert result["ma60"].iloc[-1] is None


def test_calculate_ma_empty_dataframe():
    """Test MA calculation with empty DataFrame."""
    df = pd.DataFrame()

    result = calculate_ma(df)

    # Should return empty DataFrame unchanged
    assert result.empty
    assert len(result.columns) == 0


def test_calculate_ma_missing_close_column():
    """Test MA calculation when 'close' column is missing."""
    data = {"open": [1, 2, 3, 4, 5], "high": [2, 3, 4, 5, 6], "low": [0, 1, 2, 3, 4]}
    df = pd.DataFrame(data)

    result = calculate_ma(df)

    # Should return DataFrame unchanged
    assert result.equals(df)
    assert "ma5" not in result.columns


def test_calculate_ma_with_nan_values():
    """Test MA calculation with NaN values in close column."""
    data = {"close": [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10]}
    df = pd.DataFrame(data)

    result = calculate_ma(df)

    # Check that MAs are calculated (rolling mean handles NaN)
    assert "ma5" in result.columns
    assert result["ma5"].iloc[-1] is not None

    # Check that final result has None instead of NaN
    # Note: The function replaces NaN with None, but some NaN values might remain
    # due to insufficient data for MA calculation
    # Last value should be calculated
    assert result["ma5"].iloc[-1] is not None


def test_calculate_ma_preserves_original_data():
    """Test that MA calculation doesn't modify the original DataFrame."""
    data = {
        "close": [i for i in range(1, 21)]  # 1 to 20
    }
    df = pd.DataFrame(data)
    original_df = df.copy()

    result = calculate_ma(df)

    # Original DataFrame should be unchanged
    assert df.equals(original_df)

    # Result should have additional MA columns
    assert len(result.columns) > len(df.columns)
    assert "ma5" in result.columns


def test_calculate_ma_with_string_data():
    """Test MA calculation with non-numeric data in close column."""
    data = {"close": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]}
    df = pd.DataFrame(data)

    result = calculate_ma(df)

    # Should handle string data gracefully (rolling mean will work with numeric strings)
    assert "ma5" in result.columns
    assert result["ma5"].iloc[-1] is not None


def test_calculate_ma_edge_case_exactly_ma_period():
    """Test MA calculation when data length exactly matches MA period."""
    # Create DataFrame with exactly 5 rows (exactly enough for MA5)
    data = {"close": [1, 2, 3, 4, 5]}
    df = pd.DataFrame(data)

    result = calculate_ma(df)

    # MA5 should be calculated
    assert result["ma5"].iloc[-1] is not None
    expected_ma5 = (1 + 2 + 3 + 4 + 5) / 5
    assert abs(result["ma5"].iloc[-1] - expected_ma5) < 0.001

    # Longer MAs should be None
    assert result["ma10"].iloc[-1] is None
    assert result["ma20"].iloc[-1] is None
    assert result["ma60"].iloc[-1] is None
