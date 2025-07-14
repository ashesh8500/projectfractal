import backtrader as bt
import pandas as pd
from typing import Dict, Optional, List
import yfinance as yf
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from scipy import stats
from strategy import BaseStrategy
from data_fetcher import get_stock_data

class RebalanceStrategy(bt.Strategy):
    """Backtrader strategy for periodic rebalancing."""
    
    params = (
        ('rebalance_freq', 30),  # Every nth day
        ('custom_strategy', None),  # BaseStrategy instance
    )
    
    def __init__(self):
        self.orders_log = []
        self.current_weights = {}
        self.rebalance_counter = 0

    def next(self):
        self.rebalance_counter += 1
        if self.rebalance_counter % self.p.rebalance_freq != 0:
            return
        
        try:
            # Get current prices - build proper DataFrame
            current_data = {}
            valid_datas = []
            
            for d in self.datas:
                if hasattr(d, '_name') and len(d) > 0:
                    # Get historical prices (minimum 30 days for strategy calculation)
                    lookback = min(252, len(d))  # Get up to 1 year or available data
                    if lookback < 30:
                        print(f"⚠️  Insufficient data for {d._name}: {lookback} days")
                        continue
                        
                    prices_list = []
                    dates_list = []
                    
                    for i in range(lookback):
                        if len(d) > i:
                            prices_list.append(d.close[-i])
                            dates_list.append(d.datetime.date(-i))
                    
                    # Reverse to get chronological order
                    prices_list.reverse()
                    dates_list.reverse()
                    
                    current_data[d._name] = pd.Series(prices_list, index=dates_list)
                    valid_datas.append(d)
            
            if not current_data:
                print("❌ No valid data feeds for rebalancing")
                return
                
            prices_df = pd.DataFrame(current_data)
            print(f"📊 Price data shape for rebalancing: {prices_df.shape}")
            
            # Current positions and weights
            positions = {d._name: self.getposition(d).size for d in valid_datas}
            portfolio_value = self.broker.getvalue()
            
            # Calculate current weights
            current_weights = {}
            for d in valid_datas:
                position = self.getposition(d).size
                if portfolio_value > 0:
                    weight = (position * d.close[0]) / portfolio_value
                else:
                    weight = 1.0 / len(valid_datas)  # Equal weight if no value
                current_weights[d._name] = weight
            
            print(f"💼 Current weights: {current_weights}")
            print(f"💰 Portfolio value: ${portfolio_value:.2f}")
            
            # Calculate new weights using strategy
            if self.p.custom_strategy:
                new_weights = self.p.custom_strategy.calculate_new_weights(prices_df, current_weights)
                print(f"🎯 New weights: {new_weights}")
                
                # Log weight changes
                self.log_weight_changes(current_weights, new_weights)
                
                # Rebalance - only if significant change
                orders_placed = 0
                for ticker, target_weight in new_weights.items():
                    current_weight = current_weights.get(ticker, 0)
                    weight_change = abs(target_weight - current_weight)
                    
                    if weight_change > 0.01:  # Only rebalance if change > 1%
                        try:
                            data = self.getdatabyname(ticker)
                            target_value = target_weight * portfolio_value
                            target_shares = target_value / data.close[0]
                            
                            order = self.order_target_size(data=data, target=target_shares)
                            if order:
                                orders_placed += 1
                                print(f"📋 Order placed for {ticker}: target {target_shares:.2f} shares (weight: {target_weight:.2%})")
                        except Exception as e:
                            print(f"❌ Failed to place order for {ticker}: {e}")
                
                print(f"✅ Placed {orders_placed} orders on day {len(self.datas[0])}")
            else:
                print("❌ No strategy provided for rebalancing")
                
        except Exception as e:
            print(f"❌ Error in rebalancing: {e}")
            import traceback
            traceback.print_exc()

    def log_weight_changes(self, current: Dict, new: Dict):
        changes = {t: new.get(t, 0) - current.get(t, 0) for t in set(current) | set(new)}
        self.orders_log.append({
            'date': self.datas[0].datetime.date(0),
            'changes': changes
        })

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.orders_log[-1]['orders'] = self.orders_log[-1].get('orders', []) + [{
                'asset': order.data._name,
                'size': order.executed.size,
                'price': order.executed.price
            }]

class Backtester:
    """Wrapper for running backtests with Backtrader."""
    
    def __init__(self, symbols: List[str], strategy: BaseStrategy, period: str = '5y', rebalance_freq: int = 30):
        self.symbols = symbols
        self.strategy = strategy
        self.period = period
        self.rebalance_freq = rebalance_freq
        self.cerebro = None
        self.results = None
        self.portfolio_values = None
        self.benchmark_data = None
        self.baseline_data = None

    def run(self) -> Dict:
        self.cerebro = bt.Cerebro()
        
        # Add analyzers before adding data and strategy
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        
        # Add data feeds using robust data fetcher
        print(f"🔄 Loading backtest data for {self.symbols} (period: {self.period})")
        
        for symbol in self.symbols:
            try:
                # Get data for individual symbol
                symbol_data = get_stock_data(symbol, self.period)
                
                if symbol_data.empty or symbol not in symbol_data.columns:
                    print(f"⚠️  No data for {symbol}, skipping...")
                    continue
                
                # Prepare data for backtrader (needs OHLCV format)
                price_series = symbol_data[symbol]
                
                # Create OHLCV data from Close prices (for simplicity)
                ohlcv_data = pd.DataFrame({
                    'Open': price_series,
                    'High': price_series * 1.02,  # Approximate high
                    'Low': price_series * 0.98,   # Approximate low  
                    'Close': price_series,
                    'Volume': 1000000,  # Dummy volume
                    'Adj Close': price_series
                })
                
                # Ensure index is datetime
                ohlcv_data.index = pd.to_datetime(ohlcv_data.index)
                ohlcv_data = ohlcv_data.dropna()
                
                if len(ohlcv_data) < 10:
                    print(f"⚠️  Insufficient data for {symbol} ({len(ohlcv_data)} days), skipping...")
                    continue
                
                data_feed = bt.feeds.PandasData(dataname=ohlcv_data)
                self.cerebro.adddata(data_feed, name=symbol)
                print(f"✅ Added data feed for {symbol}: {len(ohlcv_data)} days")
                
            except Exception as e:
                print(f"❌ Failed to add data for {symbol}: {e}")
                continue
        
        # Add strategy
        self.cerebro.addstrategy(RebalanceStrategy, custom_strategy=self.strategy, rebalance_freq=self.rebalance_freq)
        
        # Set initial cash
        self.cerebro.broker.setcash(100000.0)  # Arbitrary
        
        # Run
        self.results = self.cerebro.run()
        
        # Stats
        strat = self.results[0]
        stats = {
            'total_return': strat.broker.getvalue() / 100000 - 1,
            'orders_log': strat.orders_log,
        }
        
        # Get analyzer results
        try:
            stats['sharpe'] = strat.analyzers.sharpe.get_analysis()['sharperatio']
        except (KeyError, AttributeError):
            stats['sharpe'] = None
        
        try:
            stats['max_drawdown'] = strat.analyzers.drawdown.get_analysis()['max']['drawdown']
        except (KeyError, AttributeError):
            stats['max_drawdown'] = None
        
        # Store portfolio values for detailed analysis
        self._extract_portfolio_values()
        
        # Add comprehensive metrics
        stats.update(self.calculate_comprehensive_metrics())
        
        return stats

    def _extract_portfolio_values(self):
        """Extract portfolio values over time from backtest results."""
        if not self.results:
            return
            
        strat = self.results[0]
        # Get portfolio value at each time step
        portfolio_values = []
        dates = []
        
        # Extract from cerebro's broker records
        for i in range(len(strat.datas[0])):
            if i < len(strat.datas[0]):
                try:
                    # Navigate to specific date
                    for j in range(i + 1):
                        next(strat.datas[0])
                    
                    date = strat.datas[0].datetime.date(0)
                    value = strat.broker.getvalue()
                    
                    dates.append(date)
                    portfolio_values.append(value)
                except:
                    break
        
        self.portfolio_values = pd.Series(portfolio_values, index=dates)

    def calculate_comprehensive_metrics(self) -> Dict:
        """Calculate detailed performance metrics."""
        if self.portfolio_values is None or len(self.portfolio_values) < 2:
            return {}
        
        # Calculate returns
        returns = self.portfolio_values.pct_change().dropna()
        
        # Basic metrics
        total_return = (self.portfolio_values.iloc[-1] / self.portfolio_values.iloc[0]) - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # Risk metrics
        daily_vol = returns.std()
        annualized_vol = daily_vol * np.sqrt(252)
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = annualized_return / downside_vol if downside_vol > 0 else 0
        
        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # VaR and CVaR (5% confidence level)
        var_5 = np.percentile(returns, 5)
        cvar_5 = returns[returns <= var_5].mean()
        
        # Win rate
        win_rate = (returns > 0).mean()
        
        # Rolling metrics (30-day windows)
        rolling_returns = returns.rolling(30).mean() * 252
        rolling_vol = returns.rolling(30).std() * np.sqrt(252)
        rolling_sharpe = rolling_returns / rolling_vol
        
        return {
            'daily_returns': returns,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_vol,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'var_5': var_5,
            'cvar_5': cvar_5,
            'win_rate': win_rate,
            'rolling_returns': rolling_returns,
            'rolling_volatility': rolling_vol,
            'rolling_sharpe': rolling_sharpe,
            'drawdown_series': drawdown
        }

    def get_baseline_comparison(self) -> Dict:
        """Compare performance against equal-weight baseline."""
        if not self.symbols:
            return {}
        
        # Create equal-weight baseline portfolio
        try:
            baseline_data = {}
            for symbol in self.symbols:
                symbol_data = get_stock_data(symbol, self.period)
                if not symbol_data.empty and symbol in symbol_data.columns:
                    baseline_data[symbol] = symbol_data[symbol]
            
            if not baseline_data:
                return {}
            
            # Create equal-weight portfolio
            baseline_df = pd.DataFrame(baseline_data).fillna(method='ffill').dropna()
            baseline_returns = baseline_df.pct_change().dropna()
            equal_weight_returns = baseline_returns.mean(axis=1)
            
            # Calculate baseline metrics
            baseline_total_return = (1 + equal_weight_returns).cumprod().iloc[-1] - 1
            baseline_annual_return = (1 + baseline_total_return) ** (252 / len(equal_weight_returns)) - 1
            baseline_vol = equal_weight_returns.std() * np.sqrt(252)
            baseline_sharpe = baseline_annual_return / baseline_vol if baseline_vol > 0 else 0
            
            # Calculate baseline max drawdown
            baseline_cumulative = (1 + equal_weight_returns).cumprod()
            baseline_running_max = baseline_cumulative.expanding().max()
            baseline_drawdown = (baseline_cumulative - baseline_running_max) / baseline_running_max
            baseline_max_drawdown = baseline_drawdown.min()
            
            self.baseline_data = {
                'returns': equal_weight_returns,
                'cumulative_returns': baseline_cumulative,
                'total_return': baseline_total_return,
                'annualized_return': baseline_annual_return,
                'volatility': baseline_vol,
                'sharpe_ratio': baseline_sharpe,
                'max_drawdown': baseline_max_drawdown
            }
            
            return self.baseline_data
            
        except Exception as e:
            print(f"Error calculating baseline: {e}")
            return {}

    def get_benchmark_comparison(self, benchmark_symbol: str = '^GSPC') -> Dict:
        """Compare performance against market benchmark (default: S&P 500)."""
        try:
            benchmark_data = get_stock_data(benchmark_symbol, self.period)
            if benchmark_data.empty:
                return {}
            
            benchmark_prices = benchmark_data[benchmark_symbol]
            benchmark_returns = benchmark_prices.pct_change().dropna()
            
            # Calculate benchmark metrics
            benchmark_total_return = (benchmark_prices.iloc[-1] / benchmark_prices.iloc[0]) - 1
            benchmark_annual_return = (1 + benchmark_total_return) ** (252 / len(benchmark_returns)) - 1
            benchmark_vol = benchmark_returns.std() * np.sqrt(252)
            benchmark_sharpe = benchmark_annual_return / benchmark_vol if benchmark_vol > 0 else 0
            
            # Calculate benchmark max drawdown
            benchmark_cumulative = (1 + benchmark_returns).cumprod()
            benchmark_running_max = benchmark_cumulative.expanding().max()
            benchmark_drawdown = (benchmark_cumulative - benchmark_running_max) / benchmark_running_max
            benchmark_max_drawdown = benchmark_drawdown.min()
            
            # Calculate beta (if portfolio data available)
            beta = None
            if hasattr(self, 'portfolio_values') and self.portfolio_values is not None:
                portfolio_returns = self.portfolio_values.pct_change().dropna()
                
                # Align dates
                common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
                if len(common_dates) > 30:
                    aligned_portfolio = portfolio_returns.loc[common_dates]
                    aligned_benchmark = benchmark_returns.loc[common_dates]
                    
                    # Calculate beta
                    covariance = np.cov(aligned_portfolio, aligned_benchmark)[0, 1]
                    benchmark_variance = np.var(aligned_benchmark)
                    beta = covariance / benchmark_variance if benchmark_variance > 0 else None
            
            self.benchmark_data = {
                'symbol': benchmark_symbol,
                'returns': benchmark_returns,
                'cumulative_returns': benchmark_cumulative,
                'total_return': benchmark_total_return,
                'annualized_return': benchmark_annual_return,
                'volatility': benchmark_vol,
                'sharpe_ratio': benchmark_sharpe,
                'max_drawdown': benchmark_max_drawdown,
                'beta': beta
            }
            
            return self.benchmark_data
            
        except Exception as e:
            print(f"Error calculating benchmark: {e}")
            return {}

    def calculate_performance_attribution(self) -> Dict:
        """Calculate individual asset contribution to portfolio performance."""
        if not self.results or not self.symbols:
            return {}
        
        try:
            # Get individual asset data
            asset_data = {}
            for symbol in self.symbols:
                symbol_data = get_stock_data(symbol, self.period)
                if not symbol_data.empty and symbol in symbol_data.columns:
                    asset_data[symbol] = symbol_data[symbol]
            
            if not asset_data:
                return {}
            
            asset_df = pd.DataFrame(asset_data).fillna(method='ffill').dropna()
            asset_returns = asset_df.pct_change().dropna()
            
            # Calculate individual asset contributions
            attribution = {}
            for symbol in asset_returns.columns:
                asset_return = (asset_df[symbol].iloc[-1] / asset_df[symbol].iloc[0]) - 1
                attribution[symbol] = {
                    'total_return': asset_return,
                    'annualized_return': (1 + asset_return) ** (252 / len(asset_returns)) - 1,
                    'volatility': asset_returns[symbol].std() * np.sqrt(252),
                    'contribution': asset_return / len(self.symbols)  # Equal weight assumption
                }
            
            return attribution
            
        except Exception as e:
            print(f"Error calculating attribution: {e}")
            return {}

    def create_comprehensive_charts(self) -> Dict:
        """Create comprehensive performance visualization charts."""
        charts = {}
        
        # 1. Cumulative Returns Comparison
        fig1 = make_subplots(
            rows=2, cols=2,
            subplot_titles=['Cumulative Returns', 'Rolling Sharpe Ratio', 'Drawdown', 'Return Distribution'],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Portfolio cumulative returns
        if hasattr(self, 'portfolio_values') and self.portfolio_values is not None:
            portfolio_cumret = (self.portfolio_values / self.portfolio_values.iloc[0] - 1) * 100
            fig1.add_trace(
                go.Scatter(x=portfolio_cumret.index, y=portfolio_cumret.values, 
                          name='Portfolio', line=dict(color='blue')),
                row=1, col=1
            )
        
        # Baseline comparison
        if self.baseline_data:
            baseline_cumret = (self.baseline_data['cumulative_returns'] - 1) * 100
            fig1.add_trace(
                go.Scatter(x=baseline_cumret.index, y=baseline_cumret.values, 
                          name='Equal Weight Baseline', line=dict(color='red', dash='dash')),
                row=1, col=1
            )
        
        # Benchmark comparison
        if self.benchmark_data:
            benchmark_cumret = (self.benchmark_data['cumulative_returns'] - 1) * 100
            fig1.add_trace(
                go.Scatter(x=benchmark_cumret.index, y=benchmark_cumret.values, 
                          name='S&P 500', line=dict(color='green', dash='dot')),
                row=1, col=1
            )
        
        # Rolling Sharpe ratio
        if hasattr(self, 'results') and self.results:
            metrics = self.calculate_comprehensive_metrics()
            if 'rolling_sharpe' in metrics and not metrics['rolling_sharpe'].empty:
                fig1.add_trace(
                    go.Scatter(x=metrics['rolling_sharpe'].index, y=metrics['rolling_sharpe'].values, 
                              name='Rolling Sharpe', line=dict(color='purple')),
                    row=1, col=2
                )
        
        # Drawdown chart
        if hasattr(self, 'results') and self.results:
            metrics = self.calculate_comprehensive_metrics()
            if 'drawdown_series' in metrics and not metrics['drawdown_series'].empty:
                drawdown_pct = metrics['drawdown_series'] * 100
                fig1.add_trace(
                    go.Scatter(x=drawdown_pct.index, y=drawdown_pct.values, 
                              fill='tonexty', name='Drawdown', line=dict(color='red')),
                    row=2, col=1
                )
        
        # Return distribution
        if hasattr(self, 'results') and self.results:
            metrics = self.calculate_comprehensive_metrics()
            if 'daily_returns' in metrics and not metrics['daily_returns'].empty:
                returns_pct = metrics['daily_returns'] * 100
                fig1.add_trace(
                    go.Histogram(x=returns_pct.values, name='Daily Returns', 
                               opacity=0.7, nbinsx=50),
                    row=2, col=2
                )
        
        fig1.update_layout(height=800, title_text="Portfolio Performance Analysis")
        fig1.update_xaxes(title_text="Date", row=1, col=1)
        fig1.update_xaxes(title_text="Date", row=1, col=2)
        fig1.update_xaxes(title_text="Date", row=2, col=1)
        fig1.update_xaxes(title_text="Daily Return (%)", row=2, col=2)
        fig1.update_yaxes(title_text="Cumulative Return (%)", row=1, col=1)
        fig1.update_yaxes(title_text="Sharpe Ratio", row=1, col=2)
        fig1.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
        fig1.update_yaxes(title_text="Frequency", row=2, col=2)
        
        charts['performance_overview'] = fig1
        
        # 2. Risk-Return Scatter Plot
        fig2 = go.Figure()
        
        metrics_data = []
        names = []
        
        # Portfolio
        if hasattr(self, 'results') and self.results:
            portfolio_metrics = self.calculate_comprehensive_metrics()
            metrics_data.append({
                'return': portfolio_metrics.get('annualized_return', 0) * 100,
                'volatility': portfolio_metrics.get('annualized_volatility', 0) * 100,
                'sharpe': portfolio_metrics.get('sharpe_ratio', 0)
            })
            names.append('Portfolio')
        
        # Baseline
        if self.baseline_data:
            metrics_data.append({
                'return': self.baseline_data.get('annualized_return', 0) * 100,
                'volatility': self.baseline_data.get('volatility', 0) * 100,
                'sharpe': self.baseline_data.get('sharpe_ratio', 0)
            })
            names.append('Equal Weight Baseline')
        
        # Benchmark
        if self.benchmark_data:
            metrics_data.append({
                'return': self.benchmark_data.get('annualized_return', 0) * 100,
                'volatility': self.benchmark_data.get('volatility', 0) * 100,
                'sharpe': self.benchmark_data.get('sharpe_ratio', 0)
            })
            names.append('S&P 500')
        
        if metrics_data:
            colors = ['blue', 'red', 'green']
            for i, (data, name) in enumerate(zip(metrics_data, names)):
                fig2.add_trace(go.Scatter(
                    x=[data['volatility']], 
                    y=[data['return']],
                    mode='markers+text',
                    name=name,
                    text=[f"Sharpe: {data['sharpe']:.2f}"],
                    textposition="top center",
                    marker=dict(size=15, color=colors[i % len(colors)])
                ))
        
        fig2.update_layout(
            title="Risk-Return Analysis",
            xaxis_title="Annualized Volatility (%)",
            yaxis_title="Annualized Return (%)",
            showlegend=True
        )
        
        charts['risk_return'] = fig2
        
        return charts

    def generate_comprehensive_report(self) -> Dict:
        """Generate a comprehensive backtest report with all metrics and comparisons."""
        if not self.results:
            print("❌ No backtest results available. Run backtest first.")
            return {}
        
        print("📊 Generating comprehensive backtest report...")
        
        report = {
            'basic_metrics': {},
            'baseline_comparison': {},
            'benchmark_comparison': {},
            'attribution_analysis': {},
            'charts': {},
            'statistical_tests': {}
        }
        
        # 1. Calculate all metrics
        report['basic_metrics'] = self.calculate_comprehensive_metrics()
        print("✅ Calculated portfolio metrics")
        
        # 2. Baseline comparison
        report['baseline_comparison'] = self.get_baseline_comparison()
        print("✅ Calculated baseline comparison")
        
        # 3. Benchmark comparison
        report['benchmark_comparison'] = self.get_benchmark_comparison()
        print("✅ Calculated benchmark comparison")
        
        # 4. Performance attribution
        report['attribution_analysis'] = self.calculate_performance_attribution()
        print("✅ Calculated performance attribution")
        
        # 5. Create charts
        report['charts'] = self.create_comprehensive_charts()
        print("✅ Generated comprehensive charts")
        
        # 6. Statistical significance tests
        report['statistical_tests'] = self._calculate_statistical_tests()
        print("✅ Calculated statistical tests")
        
        # 7. Summary table
        report['summary_table'] = self._create_summary_table(report)
        print("✅ Created summary table")
        
        return report

    def _calculate_statistical_tests(self) -> Dict:
        """Calculate statistical significance tests for performance differences."""
        tests = {}
        
        if not (hasattr(self, 'portfolio_values') and self.portfolio_values is not None):
            return tests
        
        portfolio_returns = self.portfolio_values.pct_change().dropna()
        
        # Test against baseline
        if self.baseline_data and 'returns' in self.baseline_data:
            baseline_returns = self.baseline_data['returns']
            
            # Align dates
            common_dates = portfolio_returns.index.intersection(baseline_returns.index)
            if len(common_dates) > 30:
                aligned_portfolio = portfolio_returns.loc[common_dates]
                aligned_baseline = baseline_returns.loc[common_dates]
                
                # T-test for difference in means
                t_stat, p_value = stats.ttest_ind(aligned_portfolio, aligned_baseline)
                tests['baseline_ttest'] = {
                    'statistic': t_stat,
                    'p_value': p_value,
                    'significant': p_value < 0.05
                }
        
        # Test against benchmark
        if self.benchmark_data and 'returns' in self.benchmark_data:
            benchmark_returns = self.benchmark_data['returns']
            
            # Align dates
            common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
            if len(common_dates) > 30:
                aligned_portfolio = portfolio_returns.loc[common_dates]
                aligned_benchmark = benchmark_returns.loc[common_dates]
                
                # T-test for difference in means
                t_stat, p_value = stats.ttest_ind(aligned_portfolio, aligned_benchmark)
                tests['benchmark_ttest'] = {
                    'statistic': t_stat,
                    'p_value': p_value,
                    'significant': p_value < 0.05
                }
                
                # Information ratio
                excess_returns = aligned_portfolio - aligned_benchmark
                if len(excess_returns) > 0 and excess_returns.std() > 0:
                    information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
                    tests['information_ratio'] = information_ratio
        
        return tests

    def _create_summary_table(self, report: Dict) -> pd.DataFrame:
        """Create a summary comparison table."""
        data = []
        
        # Portfolio metrics
        if 'basic_metrics' in report and report['basic_metrics']:
            metrics = report['basic_metrics']
            data.append({
                'Strategy': 'Portfolio',
                'Total Return (%)': f"{metrics.get('total_return', 0)*100:.2f}",
                'Annualized Return (%)': f"{metrics.get('annualized_return', 0)*100:.2f}",
                'Volatility (%)': f"{metrics.get('annualized_volatility', 0)*100:.2f}",
                'Sharpe Ratio': f"{metrics.get('sharpe_ratio', 0):.3f}",
                'Sortino Ratio': f"{metrics.get('sortino_ratio', 0):.3f}",
                'Max Drawdown (%)': f"{metrics.get('max_drawdown', 0)*100:.2f}",
                'Calmar Ratio': f"{metrics.get('calmar_ratio', 0):.3f}",
                'Win Rate (%)': f"{metrics.get('win_rate', 0)*100:.1f}",
                'VaR 5% (%)': f"{metrics.get('var_5', 0)*100:.2f}"
            })
        
        # Baseline metrics
        if 'baseline_comparison' in report and report['baseline_comparison']:
            baseline = report['baseline_comparison']
            data.append({
                'Strategy': 'Equal Weight Baseline',
                'Total Return (%)': f"{baseline.get('total_return', 0)*100:.2f}",
                'Annualized Return (%)': f"{baseline.get('annualized_return', 0)*100:.2f}",
                'Volatility (%)': f"{baseline.get('volatility', 0)*100:.2f}",
                'Sharpe Ratio': f"{baseline.get('sharpe_ratio', 0):.3f}",
                'Sortino Ratio': 'N/A',
                'Max Drawdown (%)': f"{baseline.get('max_drawdown', 0)*100:.2f}",
                'Calmar Ratio': 'N/A',
                'Win Rate (%)': 'N/A',
                'VaR 5% (%)': 'N/A'
            })
        
        # Benchmark metrics
        if 'benchmark_comparison' in report and report['benchmark_comparison']:
            benchmark = report['benchmark_comparison']
            data.append({
                'Strategy': f"Benchmark ({benchmark.get('symbol', 'N/A')})",
                'Total Return (%)': f"{benchmark.get('total_return', 0)*100:.2f}",
                'Annualized Return (%)': f"{benchmark.get('annualized_return', 0)*100:.2f}",
                'Volatility (%)': f"{benchmark.get('volatility', 0)*100:.2f}",
                'Sharpe Ratio': f"{benchmark.get('sharpe_ratio', 0):.3f}",
                'Sortino Ratio': 'N/A',
                'Max Drawdown (%)': f"{benchmark.get('max_drawdown', 0)*100:.2f}",
                'Calmar Ratio': 'N/A',
                'Win Rate (%)': 'N/A',
                'VaR 5% (%)': 'N/A'
            })
        
        return pd.DataFrame(data)

    def plot(self):
        if self.cerebro:
            self.cerebro.plot()
            plt.show()

    def plot_allocation(self):
        # Use plotly for allocation over time; extract from results
        # For simplicity, placeholder
        import plotly.express as px
        # Assume weights history from log
        df = pd.DataFrame([log['changes'] for log in self.results[0].orders_log if 'changes' in log])
        fig = px.area(df, title='Allocation Over Time')
        return fig
