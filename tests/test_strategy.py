import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy import BollingerStrategy, MLStrategy, BaseStrategy

class TestStrategies(unittest.TestCase):
    
    def setUp(self):
        """Set up test data."""
        # Create mock price data
        np.random.seed(42)  # For reproducible tests
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        self.mock_prices = pd.DataFrame({
            'AAPL': np.random.randn(50).cumsum() + 150,
            'MSFT': np.random.randn(50).cumsum() + 300,
            'GOOGL': np.random.randn(50).cumsum() + 2500
        }, index=dates)
        
        self.current_weights = {'AAPL': 0.4, 'MSFT': 0.35, 'GOOGL': 0.25}
        
    def test_bollinger_strategy(self):
        """Test Bollinger Band strategy."""
        strategy = BollingerStrategy()
        
        new_weights = strategy.calculate_new_weights(self.mock_prices, self.current_weights)
        
        # Check output format
        self.assertIsInstance(new_weights, dict)
        self.assertEqual(set(new_weights.keys()), set(self.current_weights.keys()))
        
        # Check weights sum to 1
        self.assertAlmostEqual(sum(new_weights.values()), 1.0, places=2)
        
        # Check weights are within reasonable bounds
        for weight in new_weights.values():
            self.assertGreaterEqual(weight, 0)
            self.assertLessEqual(weight, 1)
            
    def test_ml_strategy(self):
        """Test ML strategy."""
        strategy = MLStrategy()
        
        new_weights = strategy.calculate_new_weights(self.mock_prices, self.current_weights)
        
        # Check output format
        self.assertIsInstance(new_weights, dict)
        
        # Check weights sum to 1
        self.assertAlmostEqual(sum(new_weights.values()), 1.0, places=2)
        
    def test_weight_clipping(self):
        """Test weight clipping functionality."""
        # Test weights that need clipping
        extreme_weights = {'AAPL': 0.9, 'MSFT': 0.05, 'GOOGL': 0.05}
        
        clipped = BaseStrategy.clip_weights(extreme_weights, min_weight=0.1, max_weight=0.6)
        
        # Check all weights are within bounds
        for weight in clipped.values():
            self.assertGreaterEqual(weight, 0.1)
            self.assertLessEqual(weight, 0.6)
            
        # Check weights still sum to 1
        self.assertAlmostEqual(sum(clipped.values()), 1.0, places=2)
        
    def test_insufficient_data_handling(self):
        """Test strategy behavior with insufficient data."""
        # Very short price series
        short_prices = self.mock_prices.head(5)
        
        strategy = BollingerStrategy()
        
        # Should not crash with insufficient data
        new_weights = strategy.calculate_new_weights(short_prices, self.current_weights)
        self.assertIsInstance(new_weights, dict)

if __name__ == '__main__':
    unittest.main()