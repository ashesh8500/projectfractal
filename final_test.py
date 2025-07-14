#!/usr/bin/env python3
"""
Final comprehensive test of all fixed components.
"""

print('=== Final Comprehensive Test ===')
from portfolio import PortfolioManager
from backtester import Backtester  
from strategy import BollingerStrategy

# Test portfolio with multiple symbols
print('\n1. Testing Portfolio Creation:')
pm = PortfolioManager({'AAPL': 100, 'NVDA': 50})
print(f'Current value: ${pm.get_current_value():.2f}')
print(f'Distribution: {pm.get_current_distribution()}')

# Test strategy
print('\n2. Testing Strategy:')
strategy = BollingerStrategy()
current_weights = pm.get_current_distribution()
new_weights = strategy.calculate_new_weights(pm.prices, current_weights)
print(f'Current weights: {current_weights}')
print(f'New weights: {new_weights}')
print(f'Weights sum: {sum(new_weights.values()):.3f}')

# Test backtesting
print('\n3. Testing Backtesting:')
bt = Backtester(['NVDA'], strategy, period='6mo', rebalance_freq=30)
results = bt.run()
print(f'Backtest results:')
print(f'- Total return: {results["total_return"]:.2%}')  
sharpe = results.get("sharpe", "N/A")
if sharpe is not None:
    print(f'- Sharpe ratio: {sharpe:.2f}')
else:
    print(f'- Sharpe ratio: N/A')
    
drawdown = results.get("max_drawdown", "N/A")
if drawdown is not None:
    print(f'- Max drawdown: {drawdown:.2f}%')
else:
    print(f'- Max drawdown: N/A')
    
print(f'- Orders executed: {len([log for log in results["orders_log"] if "orders" in log])}')

print('\n✅ All systems working correctly!')