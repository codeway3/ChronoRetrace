import logging
from datetime import date, datetime, timedelta
from typing import List
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.schemas.backtest import GridStrategyConfig, BacktestResult, Transaction, ChartDataPoint
from app.services import data_fetcher

logger = logging.getLogger(__name__)

def run_grid_backtest(db: Session, config: GridStrategyConfig) -> BacktestResult:
    """
    Runs a grid trading backtest simulation, calculating detailed performance metrics.
    """
    logger.info(f"Starting grid backtest for {config.stock_code} from {config.start_date} to {config.end_date}")

    # --- 1. Fetch and Prepare Data ---
    history_df = data_fetcher.fetch_stock_data(
        stock_code=config.stock_code,
        interval='daily',
        market_type='A_share' if '.' in config.stock_code else 'US_stock',
    )
    if history_df.empty:
        raise ValueError("Could not fetch historical data for the given stock.")
    
    history_df['trade_date'] = pd.to_datetime(history_df['trade_date']).dt.date
    mask = (history_df['trade_date'] >= config.start_date) & (history_df['trade_date'] <= config.end_date)
    backtest_df = history_df.loc[mask].copy()
    
    if backtest_df.empty:
        raise ValueError("No historical data available for the specified date range.")

    # --- 2. Initialize Strategy and Metrics ---
    grid_lines = np.linspace(config.lower_price, config.upper_price, config.grid_count + 1)
    cash_per_grid = config.total_investment / config.grid_count
    
    # State variables based on user input
    cash_balance = config.total_investment
    position_quantity = config.initial_quantity  # Start with user-defined quantity
    initial_cost_basis = config.initial_quantity * config.initial_per_share_cost
    
    # Result accumulators
    transaction_log: List[Transaction] = []
    chart_data: List[ChartDataPoint] = []
    
    # Metrics variables
    # The initial portfolio value includes the cash for the grid AND the value of initial holdings.
    initial_portfolio_value = config.total_investment + initial_cost_basis
    peak_portfolio_value = initial_portfolio_value
    max_drawdown = 0.0
    winning_trades = 0
    sell_trades = 0

    # Benchmark (Buy and Hold)
    initial_stock_price = backtest_df.iloc[0]['open']
    # Benchmark investment should be the total initial value of the portfolio
    benchmark_shares = initial_portfolio_value / initial_stock_price
    
    grids = [
        {
            "status": "open", # 'open' or 'bought'
            "buy_price": grid_lines[i], 
            "sell_price": grid_lines[i+1],
            "bought_quantity": 0,
            "cost_basis": 0.0 # Cost for the shares bought specifically by this grid slot
        } for i in range(config.grid_count)
    ]
    
    market_type = 'A_share' if '.' in config.stock_code else 'US_stock'
    
    logger.info(f"Grids initialized. Initial state: Cash={cash_balance:.2f}, Shares={position_quantity}, Initial Cost={initial_cost_basis:.2f}")

    # --- 3. Simulation Loop ---
    for _, row in backtest_df.iterrows():
        current_date = row['trade_date']
        day_low = row['low']
        day_high = row['high']

        # Process one trade per day for simplicity
        trade_executed_today = False
        for i in range(config.grid_count):
            if trade_executed_today: break
            grid = grids[i]
            
            # --- Buy Logic ---
            # Trigger a buy if the price drops below the grid's buy price and the grid slot is open
            if grid["status"] == "open" and day_low <= grid["buy_price"]:
                buy_execution_price = grid["buy_price"]
                
                if buy_execution_price <= 0: continue
                
                potential_quantity = cash_per_grid / buy_execution_price
                
                quantity_to_buy = 0
                if market_type == 'A_share':
                    num_lots = int(potential_quantity // 100)
                    if num_lots > 0:
                        quantity_to_buy = num_lots * 100
                else: # US_stock
                    quantity_to_buy = int(potential_quantity)

                if quantity_to_buy > 0:
                    actual_cost = quantity_to_buy * buy_execution_price
                    
                    if cash_balance >= actual_cost:
                        cash_balance -= actual_cost
                        position_quantity += quantity_to_buy # Add to the unified pool
                        
                        # This grid slot is now filled
                        grid.update({
                            "status": "bought",
                            "bought_quantity": quantity_to_buy,
                            "cost_basis": actual_cost
                        })
                        
                        transaction_log.append(Transaction(
                            trade_date=current_date, trade_type="buy", price=buy_execution_price,
                            quantity=quantity_to_buy
                        ))
                        trade_executed_today = True

            # --- Sell Logic (Crucial Change) ---
            # Trigger a sell if price rises above the sell price AND the grid slot was previously bought.
            # It sells from the unified position pool, which includes the initial base position.
            elif grid["status"] == "bought" and day_high >= grid["sell_price"]:
                quantity_to_sell = grid["bought_quantity"]

                # CRITICAL CHECK: Can we sell? Do we have enough shares in our total pool?
                if position_quantity >= quantity_to_sell:
                    sell_execution_price = grid["sell_price"]
                    revenue = quantity_to_sell * sell_execution_price
                    
                    cash_balance += revenue
                    position_quantity -= quantity_to_sell # Sell from the unified pool
                    
                    # PnL for this specific grid trade is calculated based on its own cost basis
                    pnl = revenue - grid["cost_basis"]
                    sell_trades += 1
                    if pnl > 0:
                        winning_trades += 1
                    
                    # This grid slot is now open again
                    grid.update({"status": "open", "bought_quantity": 0, "cost_basis": 0.0})
                    
                    transaction_log.append(Transaction(
                        trade_date=current_date, trade_type="sell", price=sell_execution_price,
                        quantity=quantity_to_sell, pnl=pnl
                    ))
                    trade_executed_today = True

        # --- Daily Portfolio and Benchmark Valuation ---
        # The value of held shares is now based on the unified pool
        current_position_value = position_quantity * row['close']
        current_portfolio_value = cash_balance + current_position_value
        
        peak_portfolio_value = max(peak_portfolio_value, current_portfolio_value)
        drawdown = (peak_portfolio_value - current_portfolio_value) / peak_portfolio_value if peak_portfolio_value > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        
        benchmark_value = benchmark_shares * row['close']
        
        chart_data.append(ChartDataPoint(
            date=current_date,
            portfolio_value=current_portfolio_value,
            benchmark_value=benchmark_value
        ))

        # --- Handle Out-of-Bounds Scenarios ---
        close_price = row['close']
        # Exceeds Upper Bound
        if config.on_exceed_upper == 'sell_all' and close_price > config.upper_price:
            if position_quantity > 0:
                logger.info(f"Price {close_price} exceeded upper bound {config.upper_price}. Selling all {position_quantity} shares.")
                revenue = position_quantity * close_price
                cash_balance += revenue
                # Note: PnL for this bulk sale isn't calculated per-grid, it's a strategy-level event.
                # The final PnL calculation will correctly reflect this.
                transaction_log.append(Transaction(
                    trade_date=current_date, trade_type="sell", price=close_price,
                    quantity=position_quantity, pnl=None # PnL is complex here, handled by total value change
                ))
                position_quantity = 0
                # Break the simulation for this stock as the strategy has concluded.
                break 
        
        # Falls Below Lower Bound
        if config.on_fall_below_lower == 'sell_all' and close_price < config.lower_price:
            if position_quantity > 0:
                logger.info(f"Price {close_price} fell below lower bound {config.lower_price}. Selling all {position_quantity} shares (Stop-Loss).")
                revenue = position_quantity * close_price
                cash_balance += revenue
                transaction_log.append(Transaction(
                    trade_date=current_date, trade_type="sell", price=close_price,
                    quantity=position_quantity, pnl=None
                ))
                position_quantity = 0
                # Break the simulation
                break

    # --- 4. Final Metrics Calculation ---
    # If the loop broke, the last chart data point might not be the final day's close.
    # We need to ensure the final value is correctly calculated.
    final_close_price = backtest_df.iloc[-1]['close']
    final_position_value = position_quantity * final_close_price
    final_portfolio_value = cash_balance + final_position_value
    
    # If the simulation ran till the end, the last chart point is accurate.
    if not chart_data or chart_data[-1].date != config.end_date:
         # If the loop broke early, we might need to add a final data point for clarity
         if not chart_data or chart_data[-1].portfolio_value != final_portfolio_value:
            chart_data.append(ChartDataPoint(
                date=backtest_df.iloc[-1]['trade_date'],
                portfolio_value=final_portfolio_value,
                benchmark_value=benchmark_shares * final_close_price
            ))
    else:
        final_portfolio_value = chart_data[-1].portfolio_value

    total_pnl = final_portfolio_value - initial_portfolio_value
    
    total_return_rate = total_pnl / initial_portfolio_value if initial_portfolio_value > 0 else 0.0
    
    total_days = (config.end_date - config.start_date).days
    years = total_days / 365.25 if total_days > 30 else 0 # Avoid annualizing very short periods
    annualized_return_rate = (1 + total_return_rate) ** (1 / years) - 1 if years > 0 and total_return_rate > -1 else 0.0
    
    win_rate = winning_trades / sell_trades if sell_trades > 0 else 0.0

    # Prepare K-line data for the frontend
    kline_data = backtest_df.to_dict(orient='records')

    result = BacktestResult(
        total_pnl=total_pnl,
        total_return_rate=total_return_rate,
        annualized_return_rate=annualized_return_rate,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        trade_count=len(transaction_log),
        chart_data=chart_data,
        kline_data=kline_data,
        transaction_log=transaction_log,
        strategy_config=config,
        market_type=market_type
    )

    logger.info(f"Finished grid backtest for {config.stock_code}. Final PnL: {total_pnl:.2f}")
    return result
