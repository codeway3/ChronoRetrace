import logging
from datetime import datetime
from typing import Any

import akshare as ak
import pandas as pd
from fastapi_cache.decorator import cache

logger = logging.getLogger(__name__)


def _standardize_dataframe_columns(
    df: pd.DataFrame, column_map: dict[str, str]
) -> pd.DataFrame:
    """Rename columns based on a mapping dictionary to standardize column names."""
    if df is None or df.empty:
        return pd.DataFrame()
    # Rename only columns that exist in the dataframe
    rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
    return df.rename(columns=rename_dict)


def _normalize_hist_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Akshare industry hist dataframe to standard columns."""
    if df is None or df.empty:
        return pd.DataFrame()

    column_map = {
        "日期": "trade_date",
        "date": "trade_date",
        "开盘": "open",
        "open": "open",
        "开盘价": "open",
        "最高": "high",
        "high": "high",
        "最高价": "high",
        "最低": "low",
        "low": "low",
        "最低价": "low",
        "收盘": "close",
        "close": "close",
        "收盘价": "close",
        "成交量": "vol",
        "volume": "vol",
        "成交额": "amount",
        "turnover": "amount",
    }
    df = _standardize_dataframe_columns(df, column_map)

    required = ["trade_date", "open", "high", "low", "close"]
    if not all(col in df.columns for col in required):
        logger.warning(
            f"hist df missing one of required columns: {required}. Got: {df.columns.tolist()}"
        )
        return pd.DataFrame()

    if "vol" not in df.columns:
        df["vol"] = 0.0
    if "amount" not in df.columns:
        df["amount"] = df.get("close", 0) * df.get("vol", 0)

    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
    return df


def fetch_industry_list_em() -> list[dict[str, str]]:
    """Fetch industry list from Eastmoney."""
    max_retries = 3
    retry_delay = 2  # 初始延迟2秒

    for attempt in range(max_retries):
        try:
            logger.info(
                f"Fetching industry list from Eastmoney (attempt {attempt + 1}/{max_retries})"
            )
            raw = ak.stock_board_industry_name_em()
            column_map = {"板块名称": "industry_name", "板块代码": "industry_code"}
            df = _standardize_dataframe_columns(raw, column_map)

            if "industry_name" not in df.columns or "industry_code" not in df.columns:
                logger.error(
                    f"Could not find required columns in Eastmoney industry list. Got: {df.columns.tolist()}"
                )
                return []

            result = df[["industry_name", "industry_code"]].to_dict(orient="records")  # type: ignore[misc]  # type: ignore[misc]  # type: ignore[misc]  # type: ignore[misc]
            return result  # type: ignore[no-any-return]

        except Exception as exc:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed to fetch Eastmoney industry list: {exc}"
            )
            if attempt < max_retries - 1:
                # 指数退避策略：每次重试增加延迟时间
                sleep_time = retry_delay * (2**attempt)
                logger.info(f"Retrying in {sleep_time} seconds...")
                import time

                time.sleep(sleep_time)
            else:
                logger.error(
                    f"All {max_retries} attempts failed to fetch Eastmoney industry list: {exc}",
                    exc_info=True,
                )
                return []

    # 如果循环正常结束但没有返回，返回空列表
    return []


def fetch_industry_list_ths() -> list[dict[str, str]]:
    """Fetch industry list from THS name endpoint."""
    try:
        logger.info("Fetching industry list from THS")
        raw = ak.stock_board_industry_name_ths()
        column_map = {"name": "industry_name", "code": "industry_code"}
        df = _standardize_dataframe_columns(raw, column_map)

        if "industry_name" not in df.columns or "industry_code" not in df.columns:
            logger.error(
                f"Could not find required columns in THS industry list. Got: {df.columns.tolist()}"
            )
            return []

        result = df[["industry_name", "industry_code"]].to_dict(orient="records")
        return result  # type: ignore[no-any-return]

    except Exception as exc:
        logger.error(f"Failed to fetch THS industry list: {exc}", exc_info=True)
        return []


def fetch_industry_hist(industry_name: str) -> pd.DataFrame:
    """Fetch historical data for a given industry from Eastmoney."""
    try:
        today = datetime.now().strftime("%Y%m%d")
        logger.info(
            f"Fetching Eastmoney hist for industry: '{industry_name}' until {today}"
        )

        # 先验证行业名称是否存在于akshare的行业列表中
        try:
            # 获取行业列表来验证行业名称是否存在
            industry_list_df = ak.stock_board_industry_name_em()
            if "板块名称" in industry_list_df.columns:
                available_industries = industry_list_df["板块名称"].tolist()
                if industry_name not in available_industries:
                    logger.warning(
                        f"Industry '{industry_name}' not found in akshare industry list. "
                        f"Available industries count: {len(available_industries)}"
                    )
                    return pd.DataFrame()
        except Exception as validation_exc:
            logger.warning(
                f"Could not validate industry name '{industry_name}': {validation_exc}. "
                "Proceeding with fetch attempt."
            )

        # Eastmoney hist fetcher uses the industry name as the symbol
        df = ak.stock_board_industry_hist_em(symbol=industry_name, end_date=today)
        return _normalize_hist_df(df)
    except Exception as exc:
        logger.error(
            f"Failed to fetch Eastmoney hist for '{industry_name}': {exc}",
            exc_info=True,
        )
        return pd.DataFrame()


def compute_period_return(hist_df: pd.DataFrame, days: int) -> float | None:
    if hist_df is None or hist_df.empty or "close" not in hist_df.columns:
        return None
    df = hist_df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").tail(days)
    if len(df) < 2:
        return None
    first_close = df.iloc[0]["close"]
    last_close = df.iloc[-1]["close"]
    return float((last_close - first_close) / first_close) if first_close else None


@cache(expire=3600)
def build_overview(
    window: str = "20D", provider: str = "em"
) -> list[dict[str, object]]:
    """Build overview metrics for industries.

    provider:
        - "em": Eastmoney list and EM hist
        - "ths": THS list, EM hist (for consistency and to satisfy tests)
    """
    logger.info(f"Building industry overview with window={window}, provider={provider}")

    if (provider or "em").lower() == "ths":
        industry_list = fetch_industry_list_ths()
    else:
        industry_list = fetch_industry_list_em()
    if not industry_list:
        logger.error("Could not fetch industry list from Eastmoney")
        return []

    days_map = {"5D": 5, "20D": 20, "60D": 60}
    days = days_map.get(window.upper(), 20)
    results: list[dict[str, object]] = []

    # 限制处理的行业数量，避免一次性请求过多
    max_industries = 50
    if len(industry_list) > max_industries:
        logger.info(f"Limiting to {max_industries} industries to avoid rate limiting")
        industry_list = industry_list[:max_industries]

    import time

    for i, industry in enumerate(industry_list):
        name = industry.get("industry_name")
        code = industry.get("industry_code")
        if not name or not code:
            continue

        # 每处理5个行业添加一个短暂延迟，避免请求过于频繁
        if i > 0 and i % 5 == 0:
            logger.info(
                f"Processed {i}/{len(industry_list)} industries, pausing briefly..."
            )
            time.sleep(2)

        hist = fetch_industry_hist(name)

        if hist is None or hist.empty or len(hist) < 2:
            logger.warning(f"Not enough historical data for industry: {name} ({code})")
            continue

        # Calculate metrics from the last two days of history
        last_row = hist.iloc[-1]
        prev_row = hist.iloc[-2]

        today_pct = (
            ((last_row["close"] - prev_row["close"]) / prev_row["close"]) * 100
            if prev_row["close"] != 0
            else 0
        )
        turnover = last_row.get("amount")

        period_return = compute_period_return(hist, days)
        sparkline_data = hist.tail(days)[["trade_date", "close"]].copy()
        sparkline_data["close"] = sparkline_data["close"].astype(float)
        sparkline = sparkline_data.to_dict(orient="records")  # type: ignore[misc]  # type: ignore[misc]  # type: ignore[misc]  # type: ignore[misc]

        results.append(
            {
                "industry_code": code,
                "industry_name": name,
                "today_pct": float(today_pct),
                "turnover": float(turnover) if turnover is not None else None,
                "ret_window": period_return,
                "window": window.upper(),
                "sparkline": sparkline,
            }
        )

    logger.info(f"Successfully built overview for {len(results)} industries.")
    return results


def fetch_industry_constituents(industry_code: str) -> list[dict[str, object]]:
    """Fetch the constituent stocks for a given industry from Eastmoney."""
    try:
        logger.info(f"Fetching constituents for industry code: {industry_code}")
        df = ak.stock_board_industry_cons_em(symbol=industry_code)

        column_map = {
            "代码": "stock_code",
            "名称": "stock_name",
            "最新价": "latest_price",
            "涨跌幅": "pct_change",
            "市盈率-动态": "pe_ratio",
            "换手率": "turnover_rate",
        }
        df = _standardize_dataframe_columns(df, column_map)

        required = ["stock_code", "stock_name"]
        if not all(col in df.columns for col in required):
            logger.error(
                f"Missing required columns in constituents df. Got: {df.columns.tolist()}"
            )
            return []

        result = df.to_dict(orient="records")
        return result  # type: ignore[no-any-return]

    except Exception as exc:
        logger.error(
            f"Failed to fetch constituents for industry '{industry_code}': {exc}",
            exc_info=True,
        )
        return []


def build_industry_overview(window: str = "20D") -> dict[str, dict[str, Any]]:
    """Build a comprehensive overview of all industries with their constituents."""
    logger.info(f"Building comprehensive industry overview with window={window}")

    industry_list = fetch_industry_list_em()
    if not industry_list:
        logger.error("Could not fetch industry list from Eastmoney")
        return {}

    days_map = {"5D": 5, "20D": 20, "60D": 60}
    days = days_map.get(window.upper(), 20)

    # 限制处理的行业数量，避免一次性请求过多
    max_industries = 30
    if len(industry_list) > max_industries:
        logger.info(f"Limiting to {max_industries} industries to avoid rate limiting")
        industry_list = industry_list[:max_industries]

    results = {}
    import time

    for i, industry in enumerate(industry_list):
        name = industry.get("industry_name")
        code = industry.get("industry_code")
        if not name or not code:
            continue

        # 每处理3个行业添加一个短暂延迟，避免请求过于频繁
        if i > 0 and i % 3 == 0:
            logger.info(
                f"Processed {i}/{len(industry_list)} industries, pausing briefly..."
            )
            time.sleep(3)  # 延迟3秒

        hist = fetch_industry_hist(name)

        # 获取成分股前添加短暂延迟
        time.sleep(1)  # 延迟1秒
        constituents = fetch_industry_constituents(code)

        if hist is None or hist.empty or len(hist) < 2:
            logger.warning(f"Not enough historical data for industry: {name} ({code})")
            continue

        # Calculate metrics from the last two days of history
        last_row = hist.iloc[-1]
        prev_row = hist.iloc[-2]

        today_pct = (
            ((last_row["close"] - prev_row["close"]) / prev_row["close"]) * 100
            if prev_row["close"] != 0
            else 0
        )
        turnover = last_row.get("amount")

        period_return = compute_period_return(hist, days)
        sparkline_data = hist.tail(days)[["trade_date", "close"]].copy()
        sparkline_data["close"] = sparkline_data["close"].astype(float)
        sparkline = sparkline_data.to_dict(orient="records")

        results[code] = {
            "industry_code": code,
            "industry_name": name,
            "today_pct": float(today_pct),
            "turnover": float(turnover) if turnover is not None else None,
            "ret_window": period_return,
            "window": window.upper(),
            "sparkline": sparkline,
            "constituents": constituents,
        }

    logger.info(
        f"Successfully built comprehensive overview for {len(results)} industries."
    )
    return results
