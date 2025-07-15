"""
Production-grade portfolio management with proper error handling and validation.
"""
import logging
from datetime import datetime
from typing import Dict, Optional, List
import pandas as pd
import numpy as np

from config import config
from data_service import get_stock_data
from exceptions import PortfolioError, ValidationError, DataFetchError

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Manages portfolio holdings, data fetching, and calculations."""
    
    def __init__(self, holdings: Dict[str, float]):
        """
        Initialize portfolio manager.
        
        Args:
            holdings: Dict[ticker: str, shares: float]
            
        Raises:
            ValidationError: If holdings are invalid
        """
        self._validate_holdings(holdings)
        
        self.holdings = holdings.copy()
        self.symbols = list(holdings.keys())
        self.prices: Optional[pd.DataFrame] = None
        self.current_prices: Optional[pd.Series] = None
        self.data_source: str = "unknown"
        self.is_using_mock_data: bool = False
        
        logger.info(f"Initialized portfolio with {len(self.symbols)} symbols: {self.symbols}")
        
        # Fetch initial price data
        self._fetch_prices()
    
    def _validate_holdings(self, holdings: Dict[str, float]) -> None:
        """Validate portfolio holdings."""
        if not holdings:
            raise ValidationError("Holdings cannot be empty")
        
        for symbol, shares in holdings.items():
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValidationError(f"Invalid symbol: {symbol}")
            
            if not isinstance(shares, (int, float)) or shares <= 0:
                raise ValidationError(f"Invalid shares for {symbol}: {shares}")
            
            if shares > 1e9:  # Reasonable upper limit
                raise ValidationError(f"Shares too large for {symbol}: {shares}")
    
    def _fetch_prices(self, period: str = None) -> None:
        """Fetch price data using the data service."""
        period = period or config.data.default_period
        
        try:
            logger.debug(f"Fetching price data for {len(self.symbols)} symbols")
            
            # Get historical data with source info
            self.prices, self.data_source = get_stock_data(self.symbols, period)
            self.current_prices = self.prices.iloc[-1].copy()
            
            # Set mock data flag based on data source
            self.is_using_mock_data = (self.data_source == "mock")
            
            logger.info(f"Successfully loaded {len(self.prices)} days of price data from {self.data_source}")
        except Exception as e:
            logger.error(f"Failed to fetch price data: {e}")
            raise DataFetchError(f"Could not fetch price data: {e}") from e
    
    def get_current_value(self) -> float:
        """
        Calculate current portfolio value.
        
        Returns:
            Total portfolio value in USD
            
        Raises:
            PortfolioError: If current prices are not available
        """
        if self.current_prices is None:
            raise PortfolioError("Current prices not available")
        
        try:
            total_value = 0.0
            
            for symbol, shares in self.holdings.items():
                if symbol in self.current_prices:
                    price = self.current_prices[symbol]
                    value = shares * price
                    total_value += value
                    logger.debug(f"{symbol}: {shares} shares × ${price:.2f} = ${value:.2f}")
                else:
                    logger.warning(f"No current price available for {symbol}")
            
            logger.info(f"Total portfolio value: ${total_value:.2f}")
            return total_value
            
        except Exception as e:
            logger.error(f"Error calculating portfolio value: {e}")
            raise PortfolioError(f"Could not calculate portfolio value: {e}") from e
    
    def get_current_weights(self) -> Dict[str, float]:
        """
        Calculate current portfolio weights by value.
        
        Returns:
            Dict mapping symbols to their weight (0-1)
            
        Raises:
            PortfolioError: If weights cannot be calculated
        """
        try:
            total_value = self.get_current_value()
            
            if total_value <= 0:
                raise PortfolioError("Portfolio has no positive value")
            
            weights = {}
            for symbol, shares in self.holdings.items():
                if symbol in self.current_prices:
                    value = shares * self.current_prices[symbol]
                    weights[symbol] = value / total_value
                else:
                    weights[symbol] = 0.0
            
            # Validate weights sum to 1 (within tolerance)
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(f"Weights sum to {total_weight:.4f}, not 1.0")
            
            logger.debug(f"Current weights: {weights}")
            return weights
            
        except Exception as e:
            logger.error(f"Error calculating portfolio weights: {e}")
            raise PortfolioError(f"Could not calculate portfolio weights: {e}") from e
    
    def get_position_values(self) -> Dict[str, float]:
        """
        Get current value of each position.
        
        Returns:
            Dict mapping symbols to their current value
        """
        if self.current_prices is None:
            raise PortfolioError("Current prices not available")
        
        values = {}
        for symbol, shares in self.holdings.items():
            if symbol in self.current_prices:
                values[symbol] = shares * self.current_prices[symbol]
            else:
                values[symbol] = 0.0
        
        return values
    
    def get_price_history(self) -> pd.DataFrame:
        """
        Get historical price data.
        
        Returns:
            DataFrame with historical prices
            
        Raises:
            PortfolioError: If price data is not available
        """
        if self.prices is None:
            raise PortfolioError("Price data not available")
        
        return self.prices.copy()
    
    def refresh_data(self, period: str = None) -> None:
        """
        Refresh price data.
        
        Args:
            period: Time period for historical data
        """
        logger.info("Refreshing portfolio data")
        self._fetch_prices(period)
    
    def add_position(self, symbol: str, shares: float) -> None:
        """
        Add or update a position.
        
        Args:
            symbol: Stock symbol
            shares: Number of shares
            
        Raises:
            ValidationError: If inputs are invalid
        """
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValidationError(f"Invalid symbol: {symbol}")
        
        if not isinstance(shares, (int, float)) or shares <= 0:
            raise ValidationError(f"Invalid shares: {shares}")
        
        self.holdings[symbol] = shares
        
        # Update symbols list if new
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            logger.info(f"Added new position: {symbol}")
            # Refresh data to include new symbol
            self.refresh_data()
        else:
            logger.info(f"Updated position: {symbol}")
    
    def remove_position(self, symbol: str) -> None:
        """
        Remove a position from the portfolio.
        
        Args:
            symbol: Stock symbol to remove
            
        Raises:
            ValidationError: If symbol doesn't exist
        """
        if symbol not in self.holdings:
            raise ValidationError(f"Symbol not in portfolio: {symbol}")
        
        del self.holdings[symbol]
        self.symbols.remove(symbol)
        
        logger.info(f"Removed position: {symbol}")
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get portfolio summary.
        
        Returns:
            Dict with portfolio summary information
        """
        try:
            total_value = self.get_current_value()
            weights = self.get_current_weights()
            position_values = self.get_position_values()
            
            return {
                'total_value': total_value,
                'num_positions': len(self.holdings),
                'symbols': self.symbols.copy(),
                'weights': weights,
                'position_values': position_values,
                'largest_position': max(weights.items(), key=lambda x: x[1]) if weights else None,
                'data_last_updated': datetime.now().isoformat(),
                'is_using_mock_data': self.is_using_mock_data
            }
            
        except Exception as e:
            logger.error(f"Error generating portfolio summary: {e}")
            raise PortfolioError(f"Could not generate portfolio summary: {e}") from e