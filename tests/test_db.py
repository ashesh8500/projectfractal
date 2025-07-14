import unittest
import tempfile
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import DBManager

class TestDBManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test database."""
        # Use temporary database for testing
        self.test_db = tempfile.NamedTemporaryFile(delete=False)
        self.test_db.close()
        self.db = DBManager(self.test_db.name)
        
    def tearDown(self):
        """Clean up test database."""
        self.db.conn.close()
        os.unlink(self.test_db.name)
        
    def test_portfolio_save_load(self):
        """Test portfolio save and load operations."""
        user_id = "test_user"
        portfolio_name = "test_portfolio"
        holdings = {"AAPL": 100, "MSFT": 50, "GOOGL": 25}
        
        # Save portfolio
        self.db.save_portfolio(user_id, portfolio_name, holdings)
        
        # Load portfolios list
        portfolios = self.db.load_portfolios(user_id)
        self.assertIn(portfolio_name, portfolios)
        
        # Load specific portfolio
        loaded_holdings = self.db.load_portfolio(user_id, portfolio_name)
        self.assertEqual(loaded_holdings, holdings)
        
    def test_portfolio_update(self):
        """Test portfolio update (overwrite)."""
        user_id = "test_user"
        portfolio_name = "test_portfolio"
        
        # Save initial portfolio
        initial_holdings = {"AAPL": 100}
        self.db.save_portfolio(user_id, portfolio_name, initial_holdings)
        
        # Update portfolio
        updated_holdings = {"AAPL": 150, "MSFT": 75}
        self.db.save_portfolio(user_id, portfolio_name, updated_holdings)
        
        # Verify update
        loaded_holdings = self.db.load_portfolio(user_id, portfolio_name)
        self.assertEqual(loaded_holdings, updated_holdings)
        
        # Verify only one entry exists
        portfolios = self.db.load_portfolios(user_id)
        self.assertEqual(portfolios.count(portfolio_name), 1)
        
    def test_strategy_save_load(self):
        """Test strategy save and load operations."""
        user_id = "test_user"
        strategy_name = "test_strategy"
        code = '''
class TestStrategy(BaseStrategy):
    def calculate_new_weights(self, prices, current_weights):
        return current_weights
'''
        
        # Save strategy
        self.db.save_strategy(user_id, strategy_name, code)
        
        # Load strategies list
        strategies = self.db.load_strategies(user_id)
        self.assertIn(strategy_name, strategies)
        
        # Load specific strategy
        loaded_code = self.db.load_strategy_code(user_id, strategy_name)
        self.assertEqual(loaded_code.strip(), code.strip())
        
    def test_nonexistent_data(self):
        """Test loading nonexistent data."""
        # Nonexistent portfolio
        result = self.db.load_portfolio("nonexistent_user", "nonexistent_portfolio")
        self.assertEqual(result, {})
        
        # Nonexistent strategy
        result = self.db.load_strategy_code("nonexistent_user", "nonexistent_strategy")
        self.assertEqual(result, "")
        
        # Nonexistent user portfolios
        result = self.db.load_portfolios("nonexistent_user")
        self.assertEqual(result, [])
        
    def test_multiple_users(self):
        """Test data isolation between users."""
        # Save portfolio for user1
        self.db.save_portfolio("user1", "portfolio1", {"AAPL": 100})
        
        # Save portfolio for user2
        self.db.save_portfolio("user2", "portfolio1", {"MSFT": 200})
        
        # Verify isolation
        user1_portfolios = self.db.load_portfolios("user1")
        user2_portfolios = self.db.load_portfolios("user2")
        
        self.assertEqual(len(user1_portfolios), 1)
        self.assertEqual(len(user2_portfolios), 1)
        
        user1_holdings = self.db.load_portfolio("user1", "portfolio1")
        user2_holdings = self.db.load_portfolio("user2", "portfolio1")
        
        self.assertEqual(user1_holdings, {"AAPL": 100})
        self.assertEqual(user2_holdings, {"MSFT": 200})

if __name__ == '__main__':
    unittest.main()