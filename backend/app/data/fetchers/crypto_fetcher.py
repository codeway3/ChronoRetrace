from typing import Any, cast

import pandas as pd
import requests

from ..managers.data_utils import calculate_ma


def get_top_cryptos(limit: int = 100) -> list[dict[str, Any]]:
    """
    Fetches the top cryptocurrencies by market capitalization from the CryptoCompare API.
    """
    url = (
        f"https://min-api.cryptocompare.com/data/top/mktcapfull?limit={limit}&tsym=USD"
    )
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "Data" in data:
            result = data["Data"]
            return cast("list[dict[str, Any]]", result)
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching crypto data: {e}")
        return []


def aggregate_ohlcv(data: list[dict[str, Any]], interval: str) -> list[dict[str, Any]]:
    """
    Aggregates daily OHLCV data to a weekly or monthly interval.
    """
    if not data:
        return []

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)

    rule_map = {"weekly": "W-MON", "monthly": "ME"}
    if interval not in rule_map:
        return data

    rule = rule_map[interval]

    agg_rules: dict[str, Any] = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volumeto": "sum",
    }

    # Pyright is strict about DataFrame.agg type; cast rules to Any for compatibility
    agg_df = df.resample(rule).agg(cast("Any", agg_rules))
    agg_df.dropna(inplace=True)

    # Calculate MAs on aggregated data
    agg_df = calculate_ma(agg_df)

    agg_df.reset_index(inplace=True)
    agg_df["time"] = agg_df["time"].apply(lambda x: int(x.timestamp()))

    result = cast("list[dict[str, Any]]", agg_df.to_dict(orient="records"))
    return result


def get_crypto_ohlcv(
    symbol: str, interval: str = "daily", limit: int = 2000
) -> list[dict[str, Any]]:
    """
    Fetches OHLCV data for a given cryptocurrency symbol and interval.
    """
    fetch_limit = limit
    if interval in ["weekly", "monthly"]:
        fetch_limit = 2000

    url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={symbol}&tsym=USD&limit={fetch_limit}"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "Data" in data and "Data" in data["Data"]:
            daily_data = data["Data"]["Data"]
            if interval in ["weekly", "monthly"]:
                return aggregate_ohlcv(daily_data, interval)

            # Calculate MAs for daily data
            df = pd.DataFrame(daily_data)
            df = calculate_ma(df)
            result = cast("list[dict[str, Any]]", df.to_dict(orient="records"))
            return result

        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching crypto OHLCV data: {e}")
        return []


if __name__ == "__main__":
    pass
