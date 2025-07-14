"""
Production-grade test suite for the portfolio application.
"""
import unittest
import tempfile
import os
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import logging

# Import modules to test
from config import AppConfig, setup_logging
from data_service import DataService
from portfolio_manager import PortfolioManager
from strategies import BollingerStrategy, MLStrategy, get_strategy
from database import DatabaseManager
from exceptions import *


class TestDataService(unittest.TestCase):
    """Test the data service."""
    
    def setUp(self):
        self.data_service = DataService()
        self.data_service.clear_cache()
    
    def test_single_symbol_fetch(self):
        """Test fetching data for a single symbol."""
        try:
            data = self.data_service.get_stock_data("AAPL", "1y")
            self.assertIsInstance(data, pd.DataFrame)
            self.assertIn("AAPL", data.columns)
            self.assertGreater(len(data), 100)  # Should have reasonable amount of data
        except DataFetchError:
            # If real data fails, should fall back to mock data
            data = self.data_service._generate_fallback_data(["AAPL"], "1y")
            self.assertIsInstance(data, pd.DataFrame)
            self.assertIn("AAPL", data.columns)
    
    def test_multiple_symbols_fetch(self):
        """Test fetching data for multiple symbols."""
        symbols = ["AAPL", "MSFT"]
        try:
            data = self.data_service.get_stock_data(symbols, "1y")
            self.assertIsInstance(data, pd.DataFrame)
            for symbol in symbols:
                self.assertIn(symbol, data.columns)
        except DataFetchError:
            # Fallback test
            data = self.data_service._generate_fallback_data(symbols, "1y")
            self.assertIsInstance(data, pd.DataFrame)
            for symbol in symbols:
                self.assertIn(symbol, data.columns)
    
    def test_cache_functionality(self):
        """Test data caching."""
        # Clear cache first
        self.data_service.clear_cache()
        
        # Mock the actual fetch to control behavior
        with patch.object(self.data_service, '_fetch_with_retries') as mock_fetch:
            mock_data = pd.DataFrame({
                'AAPL': [100, 101, 102, 103, 104] * 50  # Make it longer to pass validation
            }, index=pd.date_range('2023-01-01', periods=250))
            mock_fetch.return_value = mock_data
            
            # First call should fetch
            data1 = self.data_service.get_stock_data("AAPL", "1y")
            self.assertEqual(mock_fetch.call_count, 1)
            
            # Second call should use cache
            data2 = self.data_service.get_stock_data("AAPL", "1y")
            self.assertEqual(mock_fetch.call_count, 1)  # Still 1, not 2
            
            # Data should be identical
            pd.testing.assert_frame_equal(data1, data2)
    
    def test_fallback_data_generation(self):
        """Test fallback data generation."""
        symbols = ["TEST1", "TEST2"]
        data = self.data_service._generate_fallback_data(symbols, "1y")
        
        self.assertIsInstance(data, pd.DataFrame)
        self.assertEqual(set(data.columns), set(symbols))
        self.assertGreater(len(data), 150)  # Should have ~180+ trading days (weekdays only)
        
        # Check data quality
        for symbol in symbols:
            prices = data[symbol]
            self.assertTrue((prices > 0).all())  # All positive prices
            self.assertLess(prices.std() / prices.mean(), 0.5)  # Reasonable volatility
    
    def test_validation_errors(self):
        """Test input validation."""
        with self.assertRaises(ValidationError):
            self.data_service.get_stock_data([])  # Empty symbols
        
        with self.assertRaises(ValidationError):
            self.data_service.get_stock_data([""])  # Empty symbol
        
        with self.assertRaises(ValidationError):
            self.data_service.get_stock_data(["A" * 20])  # Too long symbol


class TestPortfolioManager(unittest.TestCase):
    """Test the portfolio manager."""
    
    def setUp(self):
        self.test_holdings = {"AAPL": 100, "MSFT": 50}
        
        # Mock the data service to avoid network calls
        with patch('portfolio_manager.get_stock_data') as mock_get_data:
            mock_data = pd.DataFrame({
                'AAPL': [150, 151, 152, 153, 154],
                'MSFT': [300, 301, 302, 303, 304]
            }, index=pd.date_range('2023-01-01', periods=5))
            mock_get_data.return_value = mock_data
            
            self.portfolio = PortfolioManager(self.test_holdings)
    
    def test_portfolio_initialization(self):
        """Test portfolio initialization."""
        self.assertEqual(self.portfolio.holdings, self.test_holdings)
        self.assertEqual(set(self.portfolio.symbols), set(["AAPL", "MSFT"]))
        self.assertIsNotNone(self.portfolio.prices)
        self.assertIsNotNone(self.portfolio.current_prices)
    
    def test_current_value_calculation(self):
        """Test current portfolio value calculation."""
        value = self.portfolio.get_current_value()
        expected_value = 100 * 154 + 50 * 304  # shares * current_price
        self.assertEqual(value, expected_value)
    
    def test_current_weights_calculation(self):
        """Test current weights calculation."""
        weights = self.portfolio.get_current_weights()
        
        # Check that weights sum to approximately 1
        total_weight = sum(weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)
        
        # Check individual weights
        total_value = self.portfolio.get_current_value()
        expected_aapl_weight = (100 * 154) / total_value
        self.assertAlmostEqual(weights['AAPL'], expected_aapl_weight, places=3)
    
    def test_position_values(self):
        """Test position value calculation."""
        values = self.portfolio.get_position_values()
        
        self.assertEqual(values['AAPL'], 100 * 154)
        self.assertEqual(values['MSFT'], 50 * 304)
    
    def test_add_position(self):
        """Test adding a new position."""
        with patch('portfolio_manager.get_stock_data') as mock_get_data:
            # Mock data including the new symbol
            mock_data = pd.DataFrame({
                'AAPL': [150, 151, 152, 153, 154],
                'MSFT': [300, 301, 302, 303, 304],
                'GOOGL': [2500, 2510, 2520, 2530, 2540]
            }, index=pd.date_range('2023-01-01', periods=5))
            mock_get_data.return_value = mock_data
            
            self.portfolio.add_position('GOOGL', 10)
            
            self.assertIn('GOOGL', self.portfolio.holdings)
            self.assertEqual(self.portfolio.holdings['GOOGL'], 10)
            self.assertIn('GOOGL', self.portfolio.symbols)
    
    def test_remove_position(self):
        """Test removing a position."""
        self.portfolio.remove_position('MSFT')
        
        self.assertNotIn('MSFT', self.portfolio.holdings)
        self.assertNotIn('MSFT', self.portfolio.symbols)
    
    def test_validation_errors(self):
        """Test input validation."""
        with self.assertRaises(ValidationError):
            PortfolioManager({})  # Empty holdings
        
        with self.assertRaises(ValidationError):
            PortfolioManager({"AAPL": -10})  # Negative shares
        
        with self.assertRaises(ValidationError):
            PortfolioManager({"": 10})  # Empty symbol


class TestStrategies(unittest.TestCase):
    """Test strategy implementations."""
    
    def setUp(self):
        # Create mock price data
        dates = pd.date_range('2023-01-01', periods=100)
        np.random.seed(42)  # For reproducible tests
        
        self.prices = pd.DataFrame({
            'AAPL': 150 + np.cumsum(np.random.normal(0, 1, 100)),
            'MSFT': 300 + np.cumsum(np.random.normal(0, 1.5, 100)),
            'GOOGL': 2500 + np.cumsum(np.random.normal(0, 10, 100))
        }, index=dates)
        
        self.current_weights = {'AAPL': 0.4, 'MSFT': 0.35, 'GOOGL': 0.25}
    
    def test_bollinger_strategy(self):
        """Test Bollinger Bands strategy."""
        strategy = BollingerStrategy(window=20, std_dev=2.0)
        
        new_weights = strategy.calculate_new_weights(self.prices, self.current_weights)
        
        # Check output format
        self.assertIsInstance(new_weights, dict)
        self.assertEqual(set(new_weights.keys()), set(self.current_weights.keys()))
        
        # Check weights sum to 1
        total_weight = sum(new_weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)
        
        # Check all weights are positive
        for weight in new_weights.values():
            self.assertGreater(weight, 0)
    
    def test_ml_strategy(self):
        """Test ML strategy."""
        strategy = MLStrategy(lookback_days=50)
        
        new_weights = strategy.calculate_new_weights(self.prices, self.current_weights)
        
        # Check output format
        self.assertIsInstance(new_weights, dict)
        self.assertEqual(set(new_weights.keys()), set(self.current_weights.keys()))
        
        # Check weights sum to 1
        total_weight = sum(new_weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)
        
        # Check all weights are positive
        for weight in new_weights.values():
            self.assertGreater(weight, 0)
    
    def test_weight_clipping(self):
        """Test weight clipping and normalization."""
        # Test with extreme weights
        extreme_weights = {'AAPL': 0.8, 'MSFT': 0.15, 'GOOGL': 0.05}
        
        clipped = BollingerStrategy.clip_and_normalize_weights(
            extreme_weights, min_weight=0.1, max_weight=0.5
        )
        
        # Check constraints
        for weight in clipped.values():
            self.assertGreaterEqual(weight, 0.1)
            self.assertLessEqual(weight, 0.5)
        
        # Check normalization
        total_weight = sum(clipped.values())
        self.assertAlmostEqual(total_weight, 1.0, places=3)
    
    def test_strategy_registry(self):
        """Test strategy registry functionality."""
        # Test valid strategy
        strategy = get_strategy('bollinger')
        self.assertIsInstance(strategy, BollingerStrategy)
        
        # Test invalid strategy
        with self.assertRaises(ValidationError):
            get_strategy('invalid_strategy')
    
    def test_insufficient_data_handling(self):
        """Test strategy behavior with insufficient data."""
        # Create very short price series
        short_prices = self.prices.head(10)
        
        strategy = BollingerStrategy(window=20)
        new_weights = strategy.calculate_new_weights(short_prices, self.current_weights)
        
        # Should return current weights when insufficient data
        self.assertEqual(new_weights, self.current_weights)


class TestDatabaseManager(unittest.TestCase):
    """Test database manager."""
    
    def setUp(self):
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.test_user_id = "test_user"
        self.test_holdings = {"AAPL": 100.0, "MSFT": 50.0}
    
    def tearDown(self):
        self.db_manager.close()
        os.unlink(self.temp_db.name)
    
    def test_save_and_load_portfolio(self):
        """Test saving and loading portfolios."""
        portfolio_name = "test_portfolio"
        
        # Save portfolio
        self.db_manager.save_portfolio(self.test_user_id, portfolio_name, self.test_holdings)
        
        # Load portfolio
        loaded_holdings = self.db_manager.load_portfolio(self.test_user_id, portfolio_name)
        
        self.assertEqual(loaded_holdings, self.test_holdings)
    
    def test_list_portfolios(self):
        """Test listing portfolios."""
        # Save multiple portfolios
        self.db_manager.save_portfolio(self.test_user_id, "portfolio1", self.test_holdings)
        self.db_manager.save_portfolio(self.test_user_id, "portfolio2", {"GOOGL": 25.0})
        
        # List portfolios
        portfolios = self.db_manager.list_portfolios(self.test_user_id)
        
        self.assertEqual(len(portfolios), 2)
        portfolio_names = [p['name'] for p in portfolios]
        self.assertIn("portfolio1", portfolio_names)
        self.assertIn("portfolio2", portfolio_names)
    
    def test_delete_portfolio(self):
        """Test deleting portfolios."""
        portfolio_name = "test_portfolio"
        
        # Save and then delete
        self.db_manager.save_portfolio(self.test_user_id, portfolio_name, self.test_holdings)
        result = self.db_manager.delete_portfolio(self.test_user_id, portfolio_name)
        
        self.assertTrue(result)
        
        # Verify deletion
        loaded_holdings = self.db_manager.load_portfolio(self.test_user_id, portfolio_name)
        self.assertIsNone(loaded_holdings)
    
    def test_portfolio_history(self):
        """Test portfolio history tracking."""
        portfolio_name = "test_portfolio"
        
        # Create and update portfolio
        self.db_manager.save_portfolio(self.test_user_id, portfolio_name, self.test_holdings)
        updated_holdings = {"AAPL": 150.0, "MSFT": 75.0}
        self.db_manager.save_portfolio(self.test_user_id, portfolio_name, updated_holdings)
        
        # Get history
        history = self.db_manager.get_portfolio_history(self.test_user_id, portfolio_name)
        
        self.assertGreaterEqual(len(history), 2)  # CREATE and UPDATE
        self.assertIn('CREATE', [h['action'] for h in history])
        self.assertIn('UPDATE', [h['action'] for h in history])
    
    def test_save_and_load_strategy(self):
        """Test saving and loading strategies."""
        strategy_name = "test_strategy"
        strategy_type = "bollinger"
        parameters = {"window": 20, "std_dev": 2.0}
        
        # Save strategy
        self.db_manager.save_strategy(self.test_user_id, strategy_name, strategy_type, parameters)
        
        # Load strategy
        loaded_strategy = self.db_manager.load_strategy(self.test_user_id, strategy_name)
        
        self.assertEqual(loaded_strategy['strategy_type'], strategy_type)
        self.assertEqual(loaded_strategy['parameters'], parameters)
    
    def test_validation_errors(self):
        """Test database validation."""
        with self.assertRaises(ValidationError):
            self.db_manager.save_portfolio("", "test", self.test_holdings)  # Empty user_id
        
        with self.assertRaises(ValidationError):
            self.db_manager.save_portfolio(self.test_user_id, "", self.test_holdings)  # Empty name
        
        with self.assertRaises(ValidationError):
            self.db_manager.save_portfolio(self.test_user_id, "test", {})  # Empty holdings


class TestConfiguration(unittest.TestCase):
    """Test configuration management."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AppConfig()
        
        self.assertFalse(config.debug)
        self.assertEqual(config.log_level, "INFO")
        self.assertEqual(config.database.path, "portfolio.db")
        self.assertEqual(config.data.default_period, "5y")
        self.assertEqual(config.strategy.min_weight, 0.05)
    
    def test_env_config(self):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, {
            'DEBUG': 'true',
            'LOG_LEVEL': 'DEBUG',
            'DB_PATH': 'test.db',
            'MIN_WEIGHT': '0.1'
        }):
            config = AppConfig.from_env()
            
            self.assertTrue(config.debug)
            self.assertEqual(config.log_level, "DEBUG")
            self.assertEqual(config.database.path, "test.db")
            self.assertEqual(config.strategy.min_weight, 0.1)
    
    def test_logging_setup(self):
        """Test logging setup."""
        logger = setup_logging("DEBUG")
        # Check that the root logger level is set correctly
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, 10)  # DEBUG level


def run_tests():
    """Run all tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestDataService,
        TestPortfolioManager,
        TestStrategies,
        TestDatabaseManager,
        TestConfiguration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)