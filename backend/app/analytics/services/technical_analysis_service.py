import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import BollingerBands

from app.analytics.schemas.technical_analysis import Indicator


class TechnicalAnalysisService:
    def calculate_indicators(
        self, df: pd.DataFrame, indicators: list[Indicator]
    ) -> pd.DataFrame:
        for ind in indicators:
            name = ind.name.upper()
            params = ind.params or {}
            if name == "MA":
                period = params.get("period", 20)
                df[f"ma_{period}"] = SMAIndicator(
                    df["close"], window=period
                ).sma_indicator()
            elif name == "EMA":
                period = params.get("period", 20)
                df[f"ema_{period}"] = EMAIndicator(
                    df["close"], window=period
                ).ema_indicator()
            elif name == "MACD":
                fast = params.get("fast", 12)
                slow = params.get("slow", 26)
                signal = params.get("signal", 9)
                macd = MACD(
                    df["close"], window_fast=fast, window_slow=slow, window_sign=signal
                )
                df["macd"] = macd.macd()
                df["macd_signal"] = macd.macd_signal()
                df["macd_hist"] = macd.macd_diff()
            elif name == "RSI":
                period = params.get("period", 14)
                df[f"rsi_{period}"] = RSIIndicator(df["close"], window=period).rsi()
            elif name == "BOLLINGER":
                period = params.get("period", 20)
                std = params.get("std", 2)
                bb = BollingerBands(df["close"], window=period, window_dev=std)
                df[f"bb_mavg_{period}"] = bb.bollinger_mavg()
                df[f"bb_hband_{period}"] = bb.bollinger_hband()
                df[f"bb_lband_{period}"] = bb.bollinger_lband()
            elif name == "STOCHASTIC":
                k = params.get("k", 14)
                d = params.get("d", 3)
                smooth = params.get("smooth", 3)
                stoch = StochasticOscillator(
                    df["high"], df["low"], df["close"], window=k, smooth_window=smooth
                )
                df["stoch_k"] = stoch.stoch()
                df["stoch_d"] = df["stoch_k"].rolling(d).mean()
        return df
