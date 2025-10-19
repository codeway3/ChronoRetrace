"""
信号生成器模块 - 根据策略定义生成交易信号
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# 常量: 用于避免魔法数字 (PLR2004)  # noqa: ERA001
MIN_DATA_POINTS_GRID = 2
MIN_DATA_POINTS_MEAN_REVERSION = 20
EPSILON_FLOAT_COMPARISON = 1e-10


class SignalGenerator:
    """信号生成器类"""

    @staticmethod
    def generate_signals(
        historical_data: pd.DataFrame, strategy_def: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        根据策略定义生成交易信号

        Args:
            historical_data: 历史数据DataFrame
            strategy_def: 策略定义字典

        Returns:
            交易信号列表
        """
        signals = []

        try:
            # 获取策略类型
            strategy_type = strategy_def.get("type", "technical")

            if strategy_type == "technical":
                signals = SignalGenerator._generate_technical_signals(
                    historical_data, strategy_def
                )
            elif strategy_type == "grid":
                signals = SignalGenerator._generate_grid_signals(
                    historical_data, strategy_def
                )
            elif strategy_type == "mean_reversion":
                signals = SignalGenerator._generate_mean_reversion_signals(
                    historical_data, strategy_def
                )
            else:
                logger.warning(f"未知的策略类型: {strategy_type}")

        except Exception:
            logger.exception("信号生成失败")

        return signals

    @staticmethod
    def _generate_technical_signals(
        historical_data: pd.DataFrame, strategy_def: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """生成技术指标信号"""
        signals = []
        conditions = strategy_def.get("conditions", [])

        for condition in conditions:
            try:
                # 评估条件
                is_met = SignalGenerator._evaluate_condition(historical_data, condition)

                if is_met:
                    signal = {
                        "action": condition.get("action", "buy"),
                        "symbol": strategy_def.get("symbol", "default"),
                        "quantity": condition.get("quantity", 1.0),
                        "condition": condition,
                        "timestamp": (
                            historical_data.index[-1]
                            if len(historical_data) > 0
                            else None
                        ),
                    }
                    signals.append(signal)

            except Exception:
                logger.exception("条件评估失败")

        return signals

    @staticmethod
    def _generate_grid_signals(
        historical_data: pd.DataFrame, strategy_def: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """生成网格交易信号"""
        signals = []

        if len(historical_data) < MIN_DATA_POINTS_MEAN_REVERSION:
            return signals

        current_price = historical_data["close"].iloc[-1]
        upper_price = strategy_def.get("upper_price")
        lower_price = strategy_def.get("lower_price")
        grid_count = strategy_def.get("grid_count", 10)

        # 计算网格间距
        if upper_price and lower_price and grid_count > 1:
            grid_spacing = (upper_price - lower_price) / (grid_count - 1)

            # 确定当前价格所在的网格位置
            grid_position = int((current_price - lower_price) / grid_spacing)

            # 生成网格信号
            signal = {
                "action": "buy" if grid_position % 2 == 0 else "sell",
                "symbol": strategy_def.get("symbol", "default"),
                "quantity": strategy_def.get("quantity_per_grid", 1.0),
                "grid_position": grid_position,
                "current_price": current_price,
                "timestamp": historical_data.index[-1],
            }
            signals.append(signal)

        return signals

    @staticmethod
    def _generate_mean_reversion_signals(
        historical_data: pd.DataFrame, strategy_def: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """生成均值回归信号"""
        signals = []

        if len(historical_data) < MIN_DATA_POINTS_GRID:
            return signals

        current_price = historical_data["close"].iloc[-1]
        lookback_period = strategy_def.get("lookback_period", 20)
        std_dev_multiplier = strategy_def.get("std_dev_multiplier", 2.0)

        # 计算均值和标准差
        mean_price = (
            historical_data["close"].rolling(window=lookback_period).mean().iloc[-1]
        )
        std_dev = (
            historical_data["close"].rolling(window=lookback_period).std().iloc[-1]
        )

        upper_band = mean_price + std_dev_multiplier * std_dev
        lower_band = mean_price - std_dev_multiplier * std_dev

        # 生成信号
        if current_price > upper_band:
            signals.append(
                {
                    "action": "sell",
                    "symbol": strategy_def.get("symbol", "default"),
                    "quantity": strategy_def.get("quantity", 1.0),
                    "current_price": current_price,
                    "upper_band": upper_band,
                    "timestamp": historical_data.index[-1],
                }
            )
        elif current_price < lower_band:
            signals.append(
                {
                    "action": "buy",
                    "symbol": strategy_def.get("symbol", "default"),
                    "quantity": strategy_def.get("quantity", 1.0),
                    "current_price": current_price,
                    "lower_band": lower_band,
                    "timestamp": historical_data.index[-1],
                }
            )

        return signals

    @staticmethod
    def _evaluate_condition(
        historical_data: pd.DataFrame, condition: dict[str, Any]
    ) -> bool:
        """评估单个条件"""
        if not historical_data.empty:
            # 获取技术指标值
            indicator_value = SignalGenerator._calculate_indicator(
                historical_data, condition
            )

            # 获取比较值和运算符
            compare_value = condition.get("value")
            if compare_value is None:
                return False
            operator = condition.get("operator", "gt")

            # 执行比较
            return SignalGenerator._apply_operator(
                indicator_value, float(compare_value), operator
            )

        return False

    @staticmethod
    def _calculate_indicator(
        historical_data: pd.DataFrame, condition: dict[str, Any]
    ) -> float:
        """计算技术指标"""
        indicator_type = condition.get("indicator")
        result: float

        if indicator_type == "sma":
            window = condition.get("window", 14)
            result = float(
                historical_data["close"].rolling(window=window).mean().iloc[-1]
            )
        elif indicator_type == "ema":
            window = condition.get("window", 14)
            result = float(historical_data["close"].ewm(span=window).mean().iloc[-1])
        elif indicator_type == "rsi":
            window = condition.get("window", 14)
            result = float(
                SignalGenerator._calculate_rsi(historical_data["close"], window)
            )
        elif indicator_type == "macd":
            fast = condition.get("fast", 12)
            slow = condition.get("slow", 26)
            signal = condition.get("signal", 9)
            result = float(
                SignalGenerator._calculate_macd(
                    historical_data["close"], fast, slow, signal
                )
            )
        elif indicator_type == "bollinger_upper":
            window = condition.get("window", 20)
            std_dev = condition.get("std_dev", 2.0)
            upper, _ = SignalGenerator._calculate_bollinger_bands(
                historical_data["close"], window, std_dev
            )
            result = float(upper)
        elif indicator_type == "bollinger_lower":
            window = condition.get("window", 20)
            std_dev = condition.get("std_dev", 2.0)
            _, lower = SignalGenerator._calculate_bollinger_bands(
                historical_data["close"], window, std_dev
            )
            result = float(lower)
        elif indicator_type == "atr":
            window = condition.get("window", 14)
            result = float(SignalGenerator._calculate_atr(historical_data, window))
        else:
            # 默认返回收盘价
            result = float(historical_data["close"].iloc[-1])

        return result

    @staticmethod
    def _apply_operator(value: float, compare_value: float, operator: str) -> bool:
        """应用比较运算符"""
        if operator == "gt":
            return value > compare_value
        elif operator == "gte":
            return value >= compare_value
        elif operator == "lt":
            return value < compare_value
        elif operator == "lte":
            return value <= compare_value
        elif operator == "eq":
            return (
                abs(value - compare_value) < EPSILON_FLOAT_COMPARISON
            )  # 浮点数比较容差
        else:
            return False

    @staticmethod
    def _calculate_rsi(prices: pd.Series, window: int = 14) -> float:
        """计算RSI指标"""
        if len(prices) < window + 1:
            return 50.0  # 默认值

        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(window=window).mean()
        loss = (-delta.clip(upper=0)).rolling(window=window).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1] if not rsi.empty else 50.0

    @staticmethod
    def _calculate_macd(
        prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> float:
        """计算MACD指标"""
        if len(prices) < slow + signal:
            return 0.0

        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()

        return (macd_line - signal_line).iloc[-1] if not macd_line.empty else 0.0

    @staticmethod
    def _calculate_bollinger_bands(
        prices: pd.Series, window: int = 20, std_dev: float = 2.0
    ) -> tuple[float, float]:
        """计算布林带"""
        if len(prices) < window:
            return prices.iloc[-1], prices.iloc[-1]

        middle_band = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)

        return upper_band.iloc[-1], lower_band.iloc[-1]

    @staticmethod
    def _calculate_atr(data: pd.DataFrame, window: int = 14) -> float:
        """计算平均真实范围(ATR)"""
        if len(data) < window + 1:
            return 0.0

        high = data["high"]
        low = data["low"]
        close = data["close"]

        # 计算真实范围
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=window).mean()

        return atr.iloc[-1] if not atr.empty else 0.0


class StrategyTemplates:
    """策略模板类"""

    @staticmethod
    def moving_average_crossover(
        fast_window: int = 10, slow_window: int = 30
    ) -> dict[str, Any]:
        """移动平均线交叉策略模板"""
        return {
            "type": "technical",
            "symbol": "default",
            "conditions": [
                {
                    "name": "金叉买入",
                    "indicator": "sma",
                    "window": fast_window,
                    "operator": "gt",
                    "value": {"indicator": "sma", "window": slow_window},
                    "action": "buy",
                    "quantity": 0.5,
                },
                {
                    "name": "死叉卖出",
                    "indicator": "sma",
                    "window": fast_window,
                    "operator": "lt",
                    "value": {"indicator": "sma", "window": slow_window},
                    "action": "sell",
                    "quantity": "all",
                },
            ],
        }

    @staticmethod
    def rsi_strategy(overbought: int = 70, oversold: int = 30) -> dict[str, Any]:
        """RSI策略模板"""
        return {
            "type": "technical",
            "symbol": "default",
            "conditions": [
                {
                    "name": "超卖买入",
                    "indicator": "rsi",
                    "window": 14,
                    "operator": "lt",
                    "value": oversold,
                    "action": "buy",
                    "quantity": 0.3,
                },
                {
                    "name": "超买卖出",
                    "indicator": "rsi",
                    "window": 14,
                    "operator": "gt",
                    "value": overbought,
                    "action": "sell",
                    "quantity": "all",
                },
            ],
        }
