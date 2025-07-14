#!/usr/bin/env python3
"""
Test script for enhanced strategy analysis features.
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import PortfolioApp
from portfolio_manager import PortfolioManager
from strategies import get_strategy, STRATEGIES

def test_strategy_analysis():
    """Test strategy analysis functionality."""
    print("Testing Strategy Analysis Features...")
    
    # Create test portfolio
    test_holdings = {
        'AAPL': 100,
        'MSFT': 50,
        'GOOGL': 25
    }
    
    try:
        # Test portfolio manager
        portfolio_manager = PortfolioManager(test_holdings)
        print("✓ Portfolio manager created successfully")
        
        # Test strategy creation with parameters
        bollinger_strategy = get_strategy('bollinger', window=20, std_dev=2.0)
        print("✓ Bollinger strategy created with parameters")
        
        ml_strategy = get_strategy('ml', lookback_days=60)
        print("✓ ML strategy created with parameters")
        
        # Test strategy execution
        prices = portfolio_manager.get_price_history()
        current_weights = portfolio_manager.get_current_weights()
        
        bollinger_weights = bollinger_strategy.calculate_new_weights(prices, current_weights)
        print("✓ Bollinger strategy executed successfully")
        
        ml_weights = ml_strategy.calculate_new_weights(prices, current_weights)
        print("✓ ML strategy executed successfully")
        
        # Test performance calculation
        app = PortfolioApp()
        performance = app.calculate_strategy_performance(prices, bollinger_weights)
        
        required_metrics = ['total_return', 'annualized_return', 'volatility', 'sharpe_ratio', 'max_drawdown']
        for metric in required_metrics:
            assert metric in performance, f"Missing metric: {metric}"
        
        print("✓ Performance calculation working correctly")
        
        # Test parameter combinations generation
        param_ranges = {
            'window': (10, 30),
            'std_dev': (1.5, 2.5)
        }
        
        combinations = app.generate_parameter_combinations(param_ranges)
        assert len(combinations) > 0, "No parameter combinations generated"
        print(f"✓ Generated {len(combinations)} parameter combinations")
        
        print("\n🎉 All enhanced features are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backtesting_simulation():
    """Test backtesting simulation."""
    print("\nTesting Backtesting Simulation...")
    
    try:
        # Create test data
        dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
        np.random.seed(42)
        
        test_prices = pd.DataFrame({
            'AAPL': 150 + np.cumsum(np.random.randn(len(dates)) * 0.02),
            'MSFT': 300 + np.cumsum(np.random.randn(len(dates)) * 0.015),
            'GOOGL': 2500 + np.cumsum(np.random.randn(len(dates)) * 0.025)
        }, index=dates)
        
        test_weights = {'AAPL': 0.4, 'MSFT': 0.35, 'GOOGL': 0.25}
        
        app = PortfolioApp()
        backtest_result = app.simulate_backtest_performance(
            test_prices, test_weights, 'Monthly', 0.1
        )
        
        required_metrics = ['total_return', 'annualized_return', 'volatility', 'sharpe_ratio', 'max_drawdown']
        for metric in required_metrics:
            assert metric in backtest_result, f"Missing backtest metric: {metric}"
        
        print("✓ Backtesting simulation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Backtesting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing Enhanced Portfolio Analysis Features\n")
    
    success1 = test_strategy_analysis()
    success2 = test_backtesting_simulation()
    
    if success1 and success2:
        print("\n✅ All tests passed! The enhanced features are ready to use.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)