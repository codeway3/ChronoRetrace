import pandas as pd
import numpy as np

def calculate_ma(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates moving averages (MA) for a given DataFrame.
    The DataFrame must have a 'close' column.

    Args:
        df (pd.DataFrame): The input DataFrame with OHLCV data.

    Returns:
        pd.DataFrame: The DataFrame with added MA columns (ma5, ma10, ma20, ma60).
    """
    if 'close' not in df.columns or df.empty:
        return df
        
    for period in [5, 10, 20, 60]:
        if len(df) >= period:
            df[f'ma{period}'] = df['close'].rolling(window=period).mean()
        else:
            df[f'ma{period}'] = np.nan # Use np.nan for consistency
    
    # Replace all occurrences of NaN with None for JSON compatibility.
    # This is more robust as it handles NaNs in any column.
    df = df.replace({np.nan: None})
            
    return df

if __name__ == '__main__':
    # Create a dummy DataFrame to test the MA calculation
    data = {
        'close': [i for i in range(1, 101)] # Simple series of numbers from 1 to 100
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
    actual_ma60_last = df_with_ma.iloc[-1]['ma60']
    print(f"Expected last MA60: {expected_ma60_last}")
    print(f"Actual last MA60:   {actual_ma60_last}")
    assert abs(expected_ma60_last - actual_ma60_last) < 0.001
    print("\nTest successful!")
