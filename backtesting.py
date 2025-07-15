"""
Comprehensive Backtesting Module
Provides vectorbt-style backtesting metrics and analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class BacktestResults:
    """Container for comprehensive backtest results similar to vectorbt"""
    
    def __init__(self, 
                 portfolio_values: pd.Series,
                 benchmark_values: pd.Series,
                 trades: List[Dict],
                 allocations: pd.DataFrame,
                 fees: float = 0.0,
                 start_value: float = 100.0):
        """
        Initialize backtest results
        
        Args:
            portfolio_values: Time series of portfolio values
            benchmark_values: Time series of benchmark values  
            trades: List of trade dictionaries
            allocations: DataFrame with datetime index and symbol columns showing weights
            fees: Total fees paid
            start_value: Starting portfolio value
        """
        self.portfolio_values = portfolio_values
        self.benchmark_values = benchmark_values
        self.trades = trades
        self.allocations = allocations
        self.fees = fees
        self.start_value = start_value
        
        # Calculate derived metrics
        self._calculate_metrics()
    
    def _calculate_metrics(self):
        """Calculate comprehensive backtest metrics"""
        
        # Basic metrics
        self.start_date = self.portfolio_values.index[0]
        self.end_date = self.portfolio_values.index[-1]
        self.period = self.end_date - self.start_date
        self.end_value = self.portfolio_values.iloc[-1]
        
        # Returns
        self.total_return_pct = ((self.end_value - self.start_value) / self.start_value) * 100
        
        if len(self.benchmark_values) > 0:
            benchmark_start = self.benchmark_values.iloc[0]
            benchmark_end = self.benchmark_values.iloc[-1]
            self.benchmark_return_pct = ((benchmark_end - benchmark_start) / benchmark_start) * 100
        else:
            self.benchmark_return_pct = 0.0
        
        # Drawdown analysis
        self._calculate_drawdown()
        
        # Trade analysis
        self._analyze_trades()
        
        # Risk metrics
        self._calculate_risk_metrics()
    
    def _calculate_drawdown(self):
        """Calculate drawdown metrics"""
        running_max = self.portfolio_values.expanding().max()
        drawdown = (self.portfolio_values - running_max) / running_max * 100
        
        self.max_drawdown_pct = abs(drawdown.min())
        
        # Calculate drawdown duration
        drawdown_start = None
        max_duration = timedelta(0)
        current_duration = timedelta(0)
        
        for i, dd in enumerate(drawdown):
            if dd < 0 and drawdown_start is None:
                drawdown_start = self.portfolio_values.index[i]
            elif dd >= 0 and drawdown_start is not None:
                current_duration = self.portfolio_values.index[i] - drawdown_start
                max_duration = max(max_duration, current_duration)
                drawdown_start = None
        
        # Handle case where drawdown extends to end
        if drawdown_start is not None:
            current_duration = self.portfolio_values.index[-1] - drawdown_start
            max_duration = max(max_duration, current_duration)
        
        self.max_drawdown_duration = max_duration
    
    def _analyze_trades(self):
        """Analyze trade performance"""
        if not self.trades:
            self._set_default_trade_metrics()
            return
        
        closed_trades = [t for t in self.trades if t.get('status') == 'closed']
        open_trades = [t for t in self.trades if t.get('status') == 'open']
        
        self.total_trades = len(self.trades)
        self.total_closed_trades = len(closed_trades)
        self.total_open_trades = len(open_trades)
        
        # Open trade PnL
        self.open_trade_pnl = sum(t.get('unrealized_pnl', 0) for t in open_trades)
        
        if closed_trades:
            returns = [t.get('return_pct', 0) for t in closed_trades]
            winning_trades = [r for r in returns if r > 0]
            losing_trades = [r for r in returns if r < 0]
            
            self.win_rate_pct = (len(winning_trades) / len(returns)) * 100
            self.best_trade_pct = max(returns) if returns else 0
            self.worst_trade_pct = min(returns) if returns else 0
            
            self.avg_winning_trade_pct = np.mean(winning_trades) if winning_trades else 0
            self.avg_losing_trade_pct = np.mean(losing_trades) if losing_trades else 0
            
            # Trade durations
            winning_durations = [t.get('duration', timedelta(0)) for t in closed_trades 
                               if t.get('return_pct', 0) > 0]
            losing_durations = [t.get('duration', timedelta(0)) for t in closed_trades 
                              if t.get('return_pct', 0) < 0]
            
            self.avg_winning_trade_duration = (np.mean([d.total_seconds() for d in winning_durations]) 
                                             if winning_durations else 0)
            self.avg_losing_trade_duration = (np.mean([d.total_seconds() for d in losing_durations]) 
                                            if losing_durations else 0)
            
            # Convert back to timedelta
            self.avg_winning_trade_duration = timedelta(seconds=self.avg_winning_trade_duration)
            self.avg_losing_trade_duration = timedelta(seconds=self.avg_losing_trade_duration)
            
            # Profit factor
            total_wins = sum(winning_trades) if winning_trades else 0
            total_losses = abs(sum(losing_trades)) if losing_trades else 0
            self.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            # Expectancy
            self.expectancy = np.mean(returns) if returns else 0
        else:
            self._set_default_trade_metrics()
    
    def _set_default_trade_metrics(self):
        """Set default values when no trades available"""
        self.total_trades = 0
        self.total_closed_trades = 0
        self.total_open_trades = 0
        self.open_trade_pnl = 0
        self.win_rate_pct = 0
        self.best_trade_pct = 0
        self.worst_trade_pct = 0
        self.avg_winning_trade_pct = 0
        self.avg_losing_trade_pct = 0
        self.avg_winning_trade_duration = timedelta(0)
        self.avg_losing_trade_duration = timedelta(0)
        self.profit_factor = 0
        self.expectancy = 0
    
    def _calculate_risk_metrics(self):
        """Calculate risk and performance metrics"""
        if len(self.portfolio_values) < 2:
            self._set_default_risk_metrics()
            return
        
        # Calculate returns
        returns = self.portfolio_values.pct_change().dropna()
        
        if len(returns) == 0:
            self._set_default_risk_metrics()
            return
        
        # Sharpe Ratio (assuming 252 trading days, 2% risk-free rate)
        risk_free_rate = 0.02
        excess_returns = returns - (risk_free_rate / 252)
        self.sharpe_ratio = np.sqrt(252) * excess_returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # Calmar Ratio
        annualized_return = (self.total_return_pct / 100) * (365.25 / self.period.days)
        self.calmar_ratio = annualized_return / (self.max_drawdown_pct / 100) if self.max_drawdown_pct > 0 else 0
        
        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else returns.std()
        self.sortino_ratio = np.sqrt(252) * excess_returns.mean() / downside_std if downside_std > 0 else 0
        
        # Omega Ratio (simplified)
        threshold = risk_free_rate / 252
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns <= threshold].sum())
        self.omega_ratio = gains / losses if losses > 0 else float('inf')
        
        # Maximum exposure (simplified)
        self.max_gross_exposure_pct = 100.0  # Assuming fully invested
    
    def _set_default_risk_metrics(self):
        """Set default risk metrics when calculation fails"""
        self.sharpe_ratio = 0
        self.calmar_ratio = 0
        self.sortino_ratio = 0
        self.omega_ratio = 0
        self.max_gross_exposure_pct = 100.0
    
    def to_dict(self) -> Dict:
        """Convert results to dictionary format similar to vectorbt"""
        return {
            'Start': self.start_date,
            'End': self.end_date,
            'Period': self.period,
            'Start Value': self.start_value,
            'End Value': self.end_value,
            'Total Return [%]': self.total_return_pct,
            'Benchmark Return [%]': self.benchmark_return_pct,
            'Max Gross Exposure [%]': self.max_gross_exposure_pct,
            'Total Fees Paid': self.fees,
            'Max Drawdown [%]': self.max_drawdown_pct,
            'Max Drawdown Duration': self.max_drawdown_duration,
            'Total Trades': self.total_trades,
            'Total Closed Trades': self.total_closed_trades,
            'Total Open Trades': self.total_open_trades,
            'Open Trade PnL': self.open_trade_pnl,
            'Win Rate [%]': self.win_rate_pct,
            'Best Trade [%]': self.best_trade_pct,
            'Worst Trade [%]': self.worst_trade_pct,
            'Avg Winning Trade [%]': self.avg_winning_trade_pct,
            'Avg Losing Trade [%]': self.avg_losing_trade_pct,
            'Avg Winning Trade Duration': self.avg_winning_trade_duration,
            'Avg Losing Trade Duration': self.avg_losing_trade_duration,
            'Profit Factor': self.profit_factor,
            'Expectancy': self.expectancy,
            'Sharpe Ratio': self.sharpe_ratio,
            'Calmar Ratio': self.calmar_ratio,
            'Omega Ratio': self.omega_ratio,
            'Sortino Ratio': self.sortino_ratio,
        }
    
    def print_summary(self):
        """Print formatted summary similar to vectorbt"""
        results = self.to_dict()
        
        print("Backtest Results Summary")
        print("=" * 50)
        
        for key, value in results.items():
            if isinstance(value, float):
                if 'Duration' in key:
                    continue  # Skip float durations, use timedelta versions
                elif '[%]' in key or 'Ratio' in key or 'Factor' in key:
                    print(f"{key:<35} {value:>15.6f}")
                else:
                    print(f"{key:<35} {value:>15.2f}")
            elif isinstance(value, (pd.Timestamp, datetime)):
                print(f"{key:<35} {value.strftime('%Y-%m-%d %H:%M:%S')}")
            elif isinstance(value, timedelta):
                print(f"{key:<35} {str(value)}")
            else:
                print(f"{key:<35} {str(value)}")

    def plot_equity_curve(self):
        """Create equity curve plot for Streamlit."""
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot portfolio value
            ax.plot(self.portfolio_values.index, self.portfolio_values.values, 
                   label='Portfolio', linewidth=2, color='blue')
            
            # Plot benchmark if available
            if len(self.benchmark_values) > 0:
                ax.plot(self.benchmark_values.index, self.benchmark_values.values,
                       label='Benchmark', linewidth=2, color='gray', alpha=0.7)
            
            ax.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Portfolio Value')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            return fig
        except ImportError:
            logger.warning("Matplotlib not available for plotting")
            return None

    def plot_drawdown(self):
        """Create drawdown underwater plot."""
        try:
            import matplotlib.pyplot as plt
            
            # Calculate drawdown
            running_max = self.portfolio_values.expanding().max()
            drawdown = (self.portfolio_values - running_max) / running_max * 100
            
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.fill_between(drawdown.index, drawdown.values, 0, 
                           color='red', alpha=0.3, label='Drawdown')
            ax.plot(drawdown.index, drawdown.values, color='red', linewidth=1)
            
            ax.set_title('Portfolio Drawdown', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Drawdown (%)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            return fig
        except ImportError:
            logger.warning("Matplotlib not available for plotting")
            return None

    def plot_allocation_timeline(self):
        """Create allocation timeline plot."""
        try:
            import matplotlib.pyplot as plt
            
            if self.allocations.empty:
                return None
                
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Create stacked area chart
            ax.stackplot(self.allocations.index, 
                        *[self.allocations[col] for col in self.allocations.columns],
                        labels=self.allocations.columns,
                        alpha=0.7)
            
            ax.set_title('Portfolio Allocation Over Time', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Allocation (%)')
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
        except ImportError:
            logger.warning("Matplotlib not available for plotting")
            return None

    def get_monthly_returns(self) -> pd.DataFrame:
        """Get monthly returns table."""
        returns = self.portfolio_values.pct_change().dropna()
        monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        
        # Create pivot table by year and month
        monthly_returns.index = pd.to_datetime(monthly_returns.index)
        df = pd.DataFrame({
            'Year': monthly_returns.index.year,
            'Month': monthly_returns.index.month,
            'Return': monthly_returns.values * 100
        })
        
        pivot = df.pivot(index='Year', columns='Month', values='Return')
        pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        return pivot.round(2)


class PortfolioBacktester:
    """Main backtesting engine"""
    
    def __init__(self, 
                 price_data: pd.DataFrame,
                 benchmark_data: Optional[pd.Series] = None):
        """
        Initialize backtester
        
        Args:
            price_data: DataFrame with datetime index and symbol columns
            benchmark_data: Series with datetime index for benchmark prices
        """
        self.price_data = price_data
        self.benchmark_data = benchmark_data
        self.logger = logging.getLogger(__name__)
    
    def run_backtest(self,
                     strategy_weights: Dict[str, float],
                     rebalance_frequency: str = 'M',  # Monthly rebalancing
                     start_value: float = 100.0,
                     transaction_cost: float = 0.001) -> BacktestResults:
        """
        Run comprehensive backtest
        
        Args:
            strategy_weights: Dictionary of symbol -> weight
            rebalance_frequency: Rebalancing frequency ('D', 'W', 'M', 'Q')
            start_value: Starting portfolio value
            transaction_cost: Transaction cost as percentage
            
        Returns:
            BacktestResults object with comprehensive metrics
        """
        try:
            # Prepare data
            aligned_data = self._align_data(strategy_weights)
            if aligned_data.empty:
                return self._create_empty_results(start_value)
            
            # Generate rebalancing dates
            rebalance_dates = self._get_rebalance_dates(aligned_data.index, rebalance_frequency)
            
            # Run simulation
            portfolio_values, allocations, trades = self._simulate_portfolio(
                aligned_data, strategy_weights, rebalance_dates, start_value, transaction_cost
            )
            
            # Prepare benchmark
            benchmark_values = self._prepare_benchmark(aligned_data.index, start_value)
            
            # Create results
            results = BacktestResults(
                portfolio_values=portfolio_values,
                benchmark_values=benchmark_values,
                trades=trades,
                allocations=allocations,
                fees=sum(t.get('fees', 0) for t in trades),
                start_value=start_value
            )
            
            self.logger.info(f"Backtest completed: {len(portfolio_values)} periods, "
                           f"{len(trades)} trades, "
                           f"{results.total_return_pct:.2f}% return")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return self._create_empty_results(start_value)
    
    def _align_data(self, strategy_weights: Dict[str, float]) -> pd.DataFrame:
        """Align price data with strategy symbols"""
        symbols = list(strategy_weights.keys())
        available_symbols = [s for s in symbols if s in self.price_data.columns]
        
        if not available_symbols:
            self.logger.warning("No symbols available in price data")
            return pd.DataFrame()
        
        return self.price_data[available_symbols].dropna()
    
    def _get_rebalance_dates(self, index: pd.DatetimeIndex, frequency: str) -> List[pd.Timestamp]:
        """Generate rebalancing dates"""
        if frequency == 'D':
            return index.tolist()
        elif frequency == 'W':
            return index.to_series().resample('W').first().index.tolist()
        elif frequency == 'M':
            return index.to_series().resample('ME').first().index.tolist()
        elif frequency == 'Q':
            return index.to_series().resample('Q').first().index.tolist()
        else:
            return [index[0], index[-1]]  # Start and end only
    
    def _simulate_portfolio(self,
                          data: pd.DataFrame,
                          weights: Dict[str, float],
                          rebalance_dates: List[pd.Timestamp],
                          start_value: float,
                          transaction_cost: float) -> Tuple[pd.Series, pd.DataFrame, List[Dict]]:
        """Simulate portfolio performance with rebalancing"""
        
        portfolio_values = []
        allocations_list = []
        trades = []
        current_positions = {}
        current_value = start_value
        
        # Initialize positions
        for symbol in data.columns:
            current_positions[symbol] = 0.0
        
        for i, date in enumerate(data.index):
            current_prices = data.loc[date]
            
            # Check if rebalancing date
            is_rebalance = date in rebalance_dates or i == 0
            
            if is_rebalance:
                # Calculate target positions
                target_positions = {}
                for symbol in data.columns:
                    weight = weights.get(symbol, 0.0)
                    target_value = current_value * weight
                    if current_prices[symbol] > 0:
                        target_positions[symbol] = target_value / current_prices[symbol]
                    else:
                        target_positions[symbol] = 0.0
                
                # Generate trades
                for symbol in data.columns:
                    current_pos = current_positions.get(symbol, 0.0)
                    target_pos = target_positions[symbol]
                    
                    if abs(target_pos - current_pos) > 1e-6:  # Avoid tiny trades
                        trade_size = target_pos - current_pos
                        trade_value = trade_size * current_prices[symbol]
                        fees = abs(trade_value) * transaction_cost
                        
                        trade = {
                            'date': date,
                            'symbol': symbol,
                            'side': 'buy' if trade_size > 0 else 'sell',
                            'quantity': abs(trade_size),
                            'price': current_prices[symbol],
                            'value': abs(trade_value),
                            'fees': fees,
                            'status': 'closed'
                        }
                        trades.append(trade)
                        
                        current_positions[symbol] = target_pos
                        current_value -= fees
            
            # Calculate portfolio value
            portfolio_value = 0.0
            allocation = {}
            
            for symbol in data.columns:
                position_value = current_positions[symbol] * current_prices[symbol]
                portfolio_value += position_value
                allocation[symbol] = current_positions[symbol] * current_prices[symbol]
            
            current_value = portfolio_value
            portfolio_values.append(portfolio_value)
            
            # Calculate allocation weights
            if portfolio_value > 0:
                allocation_weights = {k: v / portfolio_value for k, v in allocation.items()}
            else:
                allocation_weights = {k: 0.0 for k in allocation.keys()}
            
            allocation_weights['date'] = date
            allocations_list.append(allocation_weights)
        
        # Convert to Series and DataFrame
        portfolio_series = pd.Series(portfolio_values, index=data.index, name='portfolio_value')
        allocations_df = pd.DataFrame(allocations_list).set_index('date')
        
        return portfolio_series, allocations_df, trades
    
    def _prepare_benchmark(self, index: pd.DatetimeIndex, start_value: float) -> pd.Series:
        """Prepare benchmark values"""
        if self.benchmark_data is None or len(self.benchmark_data) == 0:
            # Create a simple buy-and-hold benchmark using equal weights
            if len(self.price_data.columns) > 0:
                equal_weight_portfolio = self.price_data.mean(axis=1)
                normalized = equal_weight_portfolio / equal_weight_portfolio.iloc[0] * start_value
                return normalized.reindex(index, method='ffill')
            else:
                return pd.Series([start_value] * len(index), index=index)
        else:
            # Use provided benchmark
            benchmark_aligned = self.benchmark_data.reindex(index, method='ffill')
            normalized = benchmark_aligned / benchmark_aligned.iloc[0] * start_value
            return normalized
    
    def _create_empty_results(self, start_value: float) -> BacktestResults:
        """Create empty results for failed backtests"""
        empty_series = pd.Series([start_value], index=[pd.Timestamp.now()])
        empty_df = pd.DataFrame()
        return BacktestResults(
            portfolio_values=empty_series,
            benchmark_values=empty_series,
            trades=[],
            allocations=empty_df,
            start_value=start_value
        )


def create_monthly_allocation_data(allocations: pd.DataFrame) -> pd.DataFrame:
    """
    Create monthly allocation data for visualization
    
    Args:
        allocations: DataFrame with datetime index and symbol columns showing weights
        
    Returns:
        DataFrame with monthly aggregated allocations
    """
    if allocations.empty:
        return pd.DataFrame()
    
    try:
        # Resample to monthly, taking the last value of each month
        monthly_allocations = allocations.resample('ME').last()
        
        # Add month labels
        monthly_allocations['month_label'] = monthly_allocations.index.strftime('%Y-%m')
        
        return monthly_allocations
        
    except Exception as e:
        logger.error(f"Failed to create monthly allocation data: {e}")
        return pd.DataFrame()


def generate_sample_backtest(symbols: List[str], 
                           weights: Dict[str, float],
                           days: int = 252) -> BacktestResults:
    """
    Generate a sample backtest for demonstration
    
    Args:
        symbols: List of symbol names
        weights: Dictionary of symbol weights
        days: Number of days to simulate
        
    Returns:
        BacktestResults with sample data
    """
    # Generate sample price data
    np.random.seed(42)  # For reproducible results
    dates = pd.date_range(start='2022-01-01', periods=days, freq='D')
    
    price_data = {}
    for symbol in symbols:
        # Generate realistic price movements
        returns = np.random.normal(0.0008, 0.02, days)  # ~0.08% daily return, 2% volatility
        prices = 100 * np.exp(np.cumsum(returns))  # Start at $100
        price_data[symbol] = prices
    
    price_df = pd.DataFrame(price_data, index=dates)
    
    # Create backtester and run test
    backtester = PortfolioBacktester(price_df)
    results = backtester.run_backtest(weights, rebalance_frequency='M')
    
    return results


if __name__ == "__main__":
    # Example usage
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'NVDA']
    weights = {'AAPL': 0.3, 'GOOGL': 0.3, 'MSFT': 0.2, 'NVDA': 0.2}
    
    results = generate_sample_backtest(symbols, weights)
    results.print_summary()