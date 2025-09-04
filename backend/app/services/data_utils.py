import numpy as np
import pandas as pd


def calculate_ma(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates moving averages (MA) for a given DataFrame.
    The DataFrame must have a 'close' column.
    It calculates MAs only if there is enough data for the period.
    """
    if "close" not in df.columns or df.empty:
        return df

    # Make a copy to avoid SettingWithCopyWarning
    df_copy = df.copy()

    for period in [5, 10, 20, 60]:
        # Only calculate if the number of data points is sufficient for the window
        if len(df_copy) >= period:
            df_copy[f"ma{period}"] = df_copy["close"].rolling(window=period).mean()
        else:
            # If not enough data, we can skip creating the column or fill with None
            df_copy[f"ma{period}"] = None

    # Replace all occurrences of NaN (from rolling means) with None for JSON compatibility.
    df_copy.replace({np.nan: None}, inplace=True)

    return df_copy


if __name__ == "__main__":
    # Create a dummy DataFrame to test the MA calculation
    data = {
        "close": [i for i in range(1, 101)]  # Simple series of numbers from 1 to 100
    }
    df = pd.DataFrame(data)

    # Calculate MAs
    df_with_ma = calculate_ma(df)

    print("--- Testing MA Calculation ---")
    print("Original DataFrame tail:")
    print(df.tail())
    print("\nDataFrame with MAs tail:")
    print(df_with_ma.tail())

    print("\nChecking for MA columns:")
    print(f"Columns: {df_with_ma.columns.tolist()}")

    print("\nVerifying a value:")
    # The MA60 of the last element should be the average of 41 to 100
    expected_ma60_last = sum(range(41, 101)) / 60
    actual_ma60_last = df_with_ma.iloc[-1]["ma60"]
    print(f"Expected last MA60: {expected_ma60_last}")
    print(f"Actual last MA60:   {actual_ma60_last}")
    assert abs(expected_ma60_last - actual_ma60_last) < 0.001
    print("\nTest successful!")
