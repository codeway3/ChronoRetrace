import itertools
import logging

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.data.managers import data_manager as data_fetcher
from app.schemas.backtest import (
    BacktestOptimizationResponse,
    BacktestResult,
    ChartDataPoint,
    GridStrategyConfig,
    GridStrategyOptimizeConfig,
    OptimizationResultItem,
    Transaction,
)

logger = logging.getLogger(__name__)


def run_grid_backtest(db: Session, config: GridStrategyConfig) -> BacktestResult:
    """
    Runs a grid trading backtest simulation, calculating detailed performance metrics.
    """
    logger.info(
        f"Starting grid backtest for {config.stock_code} from {config.start_date} to {config.end_date}"
    )

    # --- 1. Fetch and Prepare Data ---
    history_df = data_fetcher.fetch_stock_data(
        stock_code=config.stock_code,
        interval="daily",
        market_type="A_share" if "." in config.stock_code else "US_stock",
    )
    if history_df.empty:
        raise ValueError("Could not fetch historical data for the given stock.")

    history_df["trade_date"] = pd.to_datetime(history_df["trade_date"]).dt.date
    mask = (history_df["trade_date"] >= config.start_date) & (
        history_df["trade_date"] <= config.end_date
    )
    backtest_df = history_df.loc[mask].copy()

    if backtest_df.empty:
        raise ValueError("No historical data available for the specified date range.")

    # --- 2. Initialize Strategy and Metrics ---
    grid_lines = np.linspace(
        config.lower_price, config.upper_price, config.grid_count + 1
    )
    cash_per_grid = config.total_investment / config.grid_count

    # State variables based on user input
    cash_balance = config.total_investment
    position_quantity = config.initial_quantity  # Start with user-defined quantity
    current_cost_basis = config.initial_quantity * config.initial_per_share_cost

    # Result accumulators
    transaction_log: list[Transaction] = []
    chart_data: list[ChartDataPoint] = []

    # Metrics variables
    initial_cost_basis = current_cost_basis
    initial_portfolio_value = config.total_investment + initial_cost_basis
    peak_portfolio_value = initial_portfolio_value
    max_drawdown = 0.0
    winning_trades = 0
    sell_trades = 0

    # Benchmark (Buy and Hold)
    initial_stock_price = backtest_df.iloc[0]["open"]
    benchmark_shares = initial_portfolio_value / initial_stock_price

    grids = [
        {
            "status": "open",  # 'open' or 'bought'
            "buy_price": grid_lines[i],
            "sell_price": grid_lines[i + 1],
            "bought_quantity": 0,
            "cost_basis": 0.0,
        }
        for i in range(config.grid_count)
    ]

    market_type = "A_share" if "." in config.stock_code else "US_stock"

    logger.info(
        f"Grids initialized. Initial state: Cash={cash_balance:.2f}, Shares={position_quantity}, Initial Cost={initial_cost_basis:.2f}"
    )

    # --- 3. Simulation Loop ---
    for _, row in backtest_df.iterrows():
        current_date = row["trade_date"]
        day_low = row["low"]
        day_high = row["high"]

        trade_executed_today = False
        for i in range(config.grid_count):
            if trade_executed_today:
                break
            grid = grids[i]

            if grid["status"] == "open" and day_low <= grid["buy_price"]:
                buy_execution_price = grid["buy_price"]
                if buy_execution_price <= 0:
                    continue
                potential_quantity = cash_per_grid / buy_execution_price
                quantity_to_buy = 0
                if market_type == "A_share":
                    num_lots = int(potential_quantity // 100)
                    if num_lots > 0:
                        for lots in range(num_lots, 0, -1):
                            qty = lots * 100
                            gross_cost = qty * buy_execution_price
                            commission = max(
                                gross_cost * config.commission_rate,
                                config.min_commission,
                            )
                            total_cost = gross_cost + commission
                            if cash_balance >= total_cost:
                                quantity_to_buy = qty
                                break
                else:
                    qty = int(potential_quantity)
                    gross_cost = qty * buy_execution_price
                    commission = max(
                        gross_cost * config.commission_rate, config.min_commission
                    )
                    total_cost = gross_cost + commission
                    if cash_balance >= total_cost:
                        quantity_to_buy = qty

                if quantity_to_buy > 0:
                    gross_cost = quantity_to_buy * buy_execution_price
                    commission = max(
                        gross_cost * config.commission_rate, config.min_commission
                    )
                    total_cost = gross_cost + commission
                    cash_balance -= total_cost
                    position_quantity += quantity_to_buy
                    current_cost_basis += total_cost
                    grid.update(
                        {
                            "status": "bought",
                            "bought_quantity": quantity_to_buy,
                            "cost_basis": total_cost,
                        }
                    )
                    transaction_log.append(
                        Transaction(
                            trade_date=current_date,
                            trade_type="buy",
                            price=buy_execution_price,
                            quantity=quantity_to_buy,
                        )
                    )
                    trade_executed_today = True

            elif grid["status"] == "bought" and day_high >= grid["sell_price"]:
                quantity_to_sell = grid["bought_quantity"]
                if position_quantity >= quantity_to_sell:
                    average_cost_before_sell = (
                        current_cost_basis / position_quantity
                        if position_quantity > 0
                        else 0
                    )
                    cost_of_shares_sold = quantity_to_sell * average_cost_before_sell
                    sell_execution_price = grid["sell_price"]
                    gross_revenue = quantity_to_sell * sell_execution_price
                    commission = max(
                        gross_revenue * config.commission_rate, config.min_commission
                    )
                    stamp_duty = gross_revenue * config.stamp_duty_rate
                    total_fees = commission + stamp_duty
                    net_revenue = gross_revenue - total_fees
                    current_cost_basis -= cost_of_shares_sold
                    cash_balance += net_revenue
                    position_quantity -= quantity_to_sell
                    pnl = net_revenue - grid["cost_basis"]
                    sell_trades += 1
                    if pnl > 0:
                        winning_trades += 1
                    grid.update(
                        {"status": "open", "bought_quantity": 0, "cost_basis": 0.0}
                    )
                    transaction_log.append(
                        Transaction(
                            trade_date=current_date,
                            trade_type="sell",
                            price=sell_execution_price,
                            quantity=quantity_to_sell,
                            pnl=pnl,
                        )
                    )
                    trade_executed_today = True

        current_position_value = position_quantity * row["close"]
        current_portfolio_value = cash_balance + current_position_value
        peak_portfolio_value = max(peak_portfolio_value, current_portfolio_value)
        drawdown = (
            (peak_portfolio_value - current_portfolio_value) / peak_portfolio_value
            if peak_portfolio_value > 0
            else 0.0
        )
        max_drawdown = max(max_drawdown, drawdown)
        benchmark_value = benchmark_shares * row["close"]
        chart_data.append(
            ChartDataPoint(
                date=current_date,
                portfolio_value=current_portfolio_value,
                benchmark_value=benchmark_value,
            )
        )

        close_price = row["close"]
        if config.on_exceed_upper == "sell_all" and close_price > config.upper_price:
            if position_quantity > 0:
                logger.info(
                    f"Price {close_price} exceeded upper bound {config.upper_price}. Selling all {position_quantity} shares."
                )
                gross_revenue = position_quantity * close_price
                commission = max(
                    gross_revenue * config.commission_rate, config.min_commission
                )
                stamp_duty = gross_revenue * config.stamp_duty_rate
                net_revenue = gross_revenue - (commission + stamp_duty)
                cash_balance += net_revenue
                transaction_log.append(
                    Transaction(
                        trade_date=current_date,
                        trade_type="sell",
                        price=close_price,
                        quantity=position_quantity,
                        pnl=None,
                    )
                )
                position_quantity = 0
                current_cost_basis = 0
                break

        if (
            config.on_fall_below_lower == "sell_all"
            and close_price < config.lower_price
        ):
            if position_quantity > 0:
                logger.info(
                    f"Price {close_price} fell below lower bound {config.lower_price}. Selling all {position_quantity} shares (Stop-Loss)."
                )
                gross_revenue = position_quantity * close_price
                commission = max(
                    gross_revenue * config.commission_rate, config.min_commission
                )
                stamp_duty = gross_revenue * config.stamp_duty_rate
                net_revenue = gross_revenue - (commission + stamp_duty)
                cash_balance += net_revenue
                transaction_log.append(
                    Transaction(
                        trade_date=current_date,
                        trade_type="sell",
                        price=close_price,
                        quantity=position_quantity,
                        pnl=None,
                    )
                )
                position_quantity = 0
                current_cost_basis = 0
                break

    # --- 4. Final Metrics Calculation ---
    final_close_price = backtest_df.iloc[-1]["close"]
    final_position_value = position_quantity * final_close_price
    final_portfolio_value = cash_balance + final_position_value

    if not chart_data or chart_data[-1].date != backtest_df.iloc[-1]["trade_date"]:
        chart_data.append(
            ChartDataPoint(
                date=backtest_df.iloc[-1]["trade_date"],
                portfolio_value=final_portfolio_value,
                benchmark_value=benchmark_shares * final_close_price,
            )
        )

    portfolio_df = pd.DataFrame([item.model_dump() for item in chart_data])
    portfolio_df["date"] = pd.to_datetime(portfolio_df["date"])
    portfolio_df = portfolio_df.set_index("date")
    portfolio_df["daily_return"] = (
        portfolio_df["portfolio_value"].pct_change().fillna(0)
    )

    total_pnl = final_portfolio_value - initial_portfolio_value
    total_return_rate = (
        total_pnl / initial_portfolio_value if initial_portfolio_value > 0 else 0.0
    )

    total_days = (config.end_date - config.start_date).days
    years = total_days / 365.25 if total_days > 0 else 0

    annualized_return_rate = (
        (1 + total_return_rate) ** (1 / years) - 1
        if years > 0 and total_return_rate > -1
        else 0.0
    )

    annualized_volatility = portfolio_df["daily_return"].std() * np.sqrt(252)

    sharpe_ratio = (
        annualized_return_rate / annualized_volatility
        if annualized_volatility != 0
        else 0.0
    )

    win_rate = winning_trades / sell_trades if sell_trades > 0 else 0.0
    average_holding_cost = (
        current_cost_basis / position_quantity if position_quantity > 0 else 0.0
    )

    kline_data = backtest_df.to_dict(orient="records")

    result = BacktestResult(
        total_pnl=total_pnl,
        total_return_rate=total_return_rate,
        annualized_return_rate=annualized_return_rate,
        annualized_volatility=annualized_volatility,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        trade_count=len(transaction_log),
        chart_data=chart_data,
        kline_data=kline_data,
        transaction_log=transaction_log,
        strategy_config=config,
        market_type=market_type,
        final_holding_quantity=position_quantity,
        average_holding_cost=average_holding_cost,
    )

    logger.info(
        f"Finished grid backtest for {config.stock_code}. Final PnL: {total_pnl:.2f}"
    )
    return result


def _generate_parameter_values(param_value):
    """
    Generate parameter values from either a single value or range.

    Args:
        param_value: Either a single value (int/float) or a list [start, stop, step]

    Returns:
        List of parameter values to test
    """
    if isinstance(param_value, list):
        # Range format: [start, stop, step]
        start, stop, step = param_value
        if isinstance(start, int) and isinstance(stop, int) and isinstance(step, int):
            # Integer range
            return list(range(int(start), int(stop) + 1, int(step)))
        else:
            # Float range
            # Add small epsilon to include stop
            return list(np.arange(start, stop + step / 2, step))
    else:
        # Single value
        return [param_value]


def run_grid_optimization(
    db: Session, config: GridStrategyOptimizeConfig
) -> BacktestOptimizationResponse:
    """
    Runs parameter optimization for grid trading strategy.

    Iterates through all parameter combinations defined in the optimization config,
    runs backtests for each combination, and returns results sorted by performance.
    """
    logger.info(
        f"Starting grid optimization for {config.stock_code} from {config.start_date} to {config.end_date}"
    )

    # Generate parameter combinations
    upper_price_values = _generate_parameter_values(config.upper_price)
    lower_price_values = _generate_parameter_values(config.lower_price)
    grid_count_values = _generate_parameter_values(config.grid_count)

    # Generate all combinations
    param_combinations = list(
        itertools.product(upper_price_values, lower_price_values, grid_count_values)
    )

    logger.info(f"Generated {len(param_combinations)} parameter combinations to test")

    # Validate combinations and run backtests
    optimization_results = []
    valid_combinations = 0

    for upper_price, lower_price, grid_count in param_combinations:
        # Skip invalid combinations
        if upper_price <= lower_price:
            logger.warning(
                f"Skipping invalid combination: upper_price={upper_price} <= lower_price={lower_price}"
            )
            continue

        if grid_count <= 0:
            logger.warning(
                f"Skipping invalid combination: grid_count={grid_count} <= 0"
            )
            continue

        # Create config for this combination
        single_config = GridStrategyConfig(
            stock_code=config.stock_code,
            start_date=config.start_date,
            end_date=config.end_date,
            upper_price=float(upper_price),
            lower_price=float(lower_price),
            grid_count=int(grid_count),
            total_investment=config.total_investment,
            initial_quantity=config.initial_quantity,
            initial_per_share_cost=config.initial_per_share_cost,
            on_exceed_upper=config.on_exceed_upper,
            on_fall_below_lower=config.on_fall_below_lower,
            commission_rate=config.commission_rate,
            stamp_duty_rate=config.stamp_duty_rate,
            min_commission=config.min_commission,
        )

        try:
            # Run backtest for this parameter combination
            backtest_result = run_grid_backtest(db=db, config=single_config)

            # Create optimization result item
            result_item = OptimizationResultItem(
                parameters={
                    "upper_price": upper_price,
                    "lower_price": lower_price,
                    "grid_count": grid_count,
                },
                annualized_return_rate=backtest_result.annualized_return_rate,
                sharpe_ratio=backtest_result.sharpe_ratio,
                max_drawdown=backtest_result.max_drawdown,
                win_rate=backtest_result.win_rate,
                trade_count=backtest_result.trade_count,
            )

            optimization_results.append(result_item)
            valid_combinations += 1

            logger.debug(
                f"Completed combination {valid_combinations}: upper={upper_price}, lower={lower_price}, grid={grid_count}, return={backtest_result.annualized_return_rate:.4f}"
            )

        except Exception as e:
            logger.error(
                f"Error running backtest for combination upper={upper_price}, lower={lower_price}, grid={grid_count}: {e}"
            )
            continue

    if not optimization_results:
        raise ValueError(
            "No valid parameter combinations could be tested. Please check your parameter ranges."
        )

    logger.info(f"Successfully tested {valid_combinations} parameter combinations")

    # Find best result (by annualized return rate)
    best_result = max(optimization_results, key=lambda x: x.annualized_return_rate)

    # Sort results by annualized return rate (descending)
    optimization_results.sort(key=lambda x: x.annualized_return_rate, reverse=True)

    logger.info(
        f"Optimization completed. Best result: upper={best_result.parameters['upper_price']}, "
        f"lower={best_result.parameters['lower_price']}, grid={best_result.parameters['grid_count']}, "
        f"return={best_result.annualized_return_rate:.4f}"
    )

    return BacktestOptimizationResponse(
        optimization_results=optimization_results, best_result=best_result
    )
