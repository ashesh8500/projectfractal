import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio import PortfolioManager

class TestPortfolioManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures with mock data."""
        self.test_holdings = {"AAPL": 100, "MSFT": 50}
        
    def test_portfolio_initialization(self):
        """Test portfolio manager initialization."""
        pm = PortfolioManager(self.test_holdings)
        self.assertEqual(pm.holdings, self.test_holdings)
        self.assertEqual(set(pm.symbols), set(["AAPL", "MSFT"]))
        
    def test_single_symbol_portfolio(self):
        """Test portfolio with single symbol."""
        single_holdings = {"AAPL": 100}
        pm = PortfolioManager(single_holdings)
        self.assertEqual(pm.holdings, single_holdings)
        self.assertEqual(pm.symbols, ["AAPL"])
        
    def test_current_distribution(self):
        """Test current distribution calculation."""
        # Create portfolio with mock data
        pm = PortfolioManager({"AAPL": 100})
        
        # Mock the prices to avoid network calls
        pm.current_prices = pd.Series({"AAPL": 150.0})
        
        dist = pm.get_current_distribution()
        self.assertIsInstance(dist, dict)
        self.assertAlmostEqual(sum(dist.values()), 1.0, places=2)
        
    def test_current_value(self):
        """Test current value calculation."""
        pm = PortfolioManager({"AAPL": 100})
        pm.current_prices = pd.Series({"AAPL": 150.0})
        
        value = pm.get_current_value()
        self.assertEqual(value, 15000.0)  # 100 shares * $150
        
    def test_orders_calculation(self):
        """Test order calculation."""
        pm = PortfolioManager({"AAPL": 100, "MSFT": 50})
        pm.current_prices = pd.Series({"AAPL": 150.0, "MSFT": 300.0})
        
        # New weights that would require rebalancing
        new_weights = {"AAPL": 0.7, "MSFT": 0.3}
        
        orders = pm.get_orders_today(new_weights)
        self.assertIsInstance(orders, pd.DataFrame)

if __name__ == '__main__':
    unittest.main()