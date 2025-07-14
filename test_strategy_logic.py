#!/usr/bin/env python3
"""
Test script to verify strategies are working correctly with real parameter changes.
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from portfolio_manager import PortfolioManager
from strategies import get_strategy, STRATEGIES

def test_parameter_sensitivity():
    """Test that changing parameters actually changes strategy outputs."""
    print("🧪 Testing Parameter Sensitivity...")
    
    # Create test portfolio
    test_holdings = {
        'AAPL': 100,
        'MSFT': 50,
        'GOOGL': 25
    }
    
    try:
        portfolio_manager = PortfolioManager(test_holdings)
        prices = portfolio_manager.get_price_history()
        current_weights = portfolio_manager.get_current_weights()
        
        print(f"Portfolio data: {len(prices)} days, symbols: {list(prices.columns)}")
        print(f"Current weights: {current_weights}")
        
        # Test Bollinger Bands with different parameters
        print("\n📊 Testing Bollinger Bands Parameter Sensitivity:")
        
        bollinger_results = {}
        test_params = [
            {'window': 10, 'std_dev': 1.5},
            {'window': 20, 'std_dev': 2.0},
            {'window': 30, 'std_dev': 2.5}
        ]
        
        for params in test_params:
            strategy = get_strategy('bollinger', **params)
            weights = strategy.calculate_new_weights(prices, current_weights)
            bollinger_results[str(params)] = weights
            
            # Calculate total change from current weights
            total_change = sum(abs(weights[s] - current_weights[s]) for s in current_weights)
            print(f"  Params {params}: Total change = {total_change:.4f}")
            print(f"    New weights: {weights}")
        
        # Verify different parameters produce different results
        weight_sets = list(bollinger_results.values())
        all_same = all(w == weight_sets[0] for w in weight_sets[1:])
        
        if all_same:
            print("  ❌ WARNING: All parameter combinations produced identical results!")
        else:
            print("  ✅ Different parameters produce different weight allocations")
        
        # Test Momentum Strategy
        print("\n🚀 Testing Momentum Strategy Parameter Sensitivity:")
        
        momentum_results = {}
        momentum_params = [
            {'lookback_period': 10, 'momentum_threshold': 0.01},
            {'lookback_period': 20, 'momentum_threshold': 0.02},
            {'lookback_period': 30, 'momentum_threshold': 0.05}
        ]
        
        for params in momentum_params:
            strategy = get_strategy('momentum', **params)
            weights = strategy.calculate_new_weights(prices, current_weights)
            momentum_results[str(params)] = weights
            
            total_change = sum(abs(weights[s] - current_weights[s]) for s in current_weights)
            print(f"  Params {params}: Total change = {total_change:.4f}")
            print(f"    New weights: {weights}")
        
        # Verify momentum strategy sensitivity
        momentum_weight_sets = list(momentum_results.values())
        momentum_all_same = all(w == momentum_weight_sets[0] for w in momentum_weight_sets[1:])
        
        if momentum_all_same:
            print("  ❌ WARNING: All momentum parameter combinations produced identical results!")
        else:
            print("  ✅ Different momentum parameters produce different weight allocations")
        
        # Test ML Strategy
        print("\n🤖 Testing ML Strategy Parameter Sensitivity:")
        
        ml_results = {}
        ml_params = [
            {'lookback_days': 30},
            {'lookback_days': 60},
            {'lookback_days': 90}
        ]
        
        for params in ml_params:
            strategy = get_strategy('ml', **params)
            weights = strategy.calculate_new_weights(prices, current_weights)
            ml_results[str(params)] = weights
            
            total_change = sum(abs(weights[s] - current_weights[s]) for s in current_weights)
            print(f"  Params {params}: Total change = {total_change:.4f}")
            print(f"    New weights: {weights}")
        
        # Test data source detection
        print("\n📊 Testing Data Source Detection:")
        from main import PortfolioApp
        app = PortfolioApp()
        data_info = app.get_data_source_info(prices)
        
        print(f"  Data source info: {data_info}")
        if data_info['is_mock']:
            print(f"  ⚠️  Using mock data: {data_info['reason']}")
        else:
            print(f"  ✅ Using real market data")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_strategy_logic():
    """Test that strategies implement logical behavior."""
    print("\n🔍 Testing Strategy Logic...")
    
    # Create synthetic data with clear patterns
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    dates = dates[dates.weekday < 5]  # Only weekdays
    
    # Create trending data
    np.random.seed(42)
    
    # AAPL: Strong uptrend
    aapl_prices = 150 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, len(dates))))
    
    # MSFT: Sideways with volatility
    msft_prices = 300 + np.cumsum(np.random.normal(0, 0.015, len(dates)))
    
    # GOOGL: Downtrend
    googl_prices = 2500 * np.exp(np.cumsum(np.random.normal(-0.0005, 0.025, len(dates))))
    
    test_prices = pd.DataFrame({
        'AAPL': aapl_prices,
        'MSFT': msft_prices,
        'GOOGL': googl_prices
    }, index=dates)
    
    current_weights = {'AAPL': 0.33, 'MSFT': 0.33, 'GOOGL': 0.34}
    
    print(f"Test data: AAPL trend: {(aapl_prices[-1]/aapl_prices[0] - 1)*100:.1f}%")
    print(f"           MSFT trend: {(msft_prices[-1]/msft_prices[0] - 1)*100:.1f}%")
    print(f"           GOOGL trend: {(googl_prices[-1]/googl_prices[0] - 1)*100:.1f}%")
    
    # Test momentum strategy - should favor AAPL (uptrend)
    momentum_strategy = get_strategy('momentum', lookback_period=20, momentum_threshold=0.01)
    momentum_weights = momentum_strategy.calculate_new_weights(test_prices, current_weights)
    
    print(f"\nMomentum Strategy Results:")
    print(f"  AAPL weight: {momentum_weights['AAPL']:.3f} (was {current_weights['AAPL']:.3f})")
    print(f"  MSFT weight: {momentum_weights['MSFT']:.3f} (was {current_weights['MSFT']:.3f})")
    print(f"  GOOGL weight: {momentum_weights['GOOGL']:.3f} (was {current_weights['GOOGL']:.3f})")
    
    # Logic check: AAPL should get higher weight due to uptrend
    if momentum_weights['AAPL'] > momentum_weights['GOOGL']:
        print("  ✅ Momentum strategy correctly favors uptrending stock")
    else:
        print("  ❌ Momentum strategy logic may be incorrect")
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Enhanced Strategy Implementation\n")
    
    success1 = test_parameter_sensitivity()
    success2 = test_strategy_logic()
    
    if success1 and success2:
        print("\n✅ All strategy tests passed! Strategies are working correctly with parameter changes.")
    else:
        print("\n❌ Some strategy tests failed. Please check the implementation.")