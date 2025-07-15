"""
Production-grade data fetcher with robust error handling and caching.
Enhanced with multiple data sources for professional financial terminal.
"""
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from functools import lru_cache

from config import config
from exceptions import DataFetchError, ValidationError

logger = logging.getLogger(__name__)


class DataService:
    """Production-grade data service with caching and fallbacks."""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # (data, timestamp, is_mock, source)
        self._using_mock_data = False
        self._current_data_source = "unknown"
        
        # Data source priority: yfinance -> Alpha Vantage -> mock
        self._data_sources = [
            ("yfinance", self._fetch_yfinance),
            ("alpha_vantage", self._fetch_alpha_vantage),
            ("mock", self._generate_fallback_data)
        ]

    def get_stock_data(self, symbols: Union[str, List[str]], period: str = None) -> Tuple[pd.DataFrame, str]:
        """
        Fetch stock data with robust error handling and multiple sources.

        Args:
            symbols: Single symbol or list of symbols
            period: Time period (1y, 2y, 5y, etc.)

        Returns:
            Tuple of (DataFrame with Close prices for each symbol, data_source)

        Raises:
            DataFetchError: When data cannot be fetched
            ValidationError: When data validation fails
        """
        period = period or config.data.default_period

        # Normalize symbols to list
        if isinstance(symbols, str):
            symbols = [symbols.upper()]
        else:
            symbols = [symbol.upper() for symbol in symbols]

        # Validate symbols
        self._validate_symbols(symbols)

        # Check cache first
        cache_key = f"{','.join(sorted(symbols))}_{period}"
        cached_result = self._get_cached_data(cache_key)
        if cached_result is not None:
            cached_data, is_mock, source = cached_result
            logger.debug(f"Using cached data for {symbols} from {source}")
            return cached_data, source

        # Try data sources in priority order
        for source_name, fetch_func in self._data_sources:
            try:
                if source_name == "alpha_vantage" and not hasattr(config, 'alpha_vantage_key'):
                    continue  # Skip if no API key configured
                    
                logger.info(f"Attempting to fetch data from {source_name} for {symbols}")
                data = fetch_func(symbols, period)
                
                if data is not None and not data.empty:
                    self._validate_data(data, symbols)
                    
                    # Cache the result
                    is_mock = source_name == "mock"
                    self._cache[cache_key] = (data, time.time(), is_mock, source_name)
                    self._using_mock_data = is_mock
                    self._current_data_source = source_name
                    
                    logger.info(f"Successfully fetched data from {source_name} for {len(symbols)} symbols")
                    return data, source_name
                    
            except Exception as e:
                logger.warning(f"Failed to fetch data from {source_name}: {e}")
                continue
        
        # If all sources failed
        raise DataFetchError(f"Failed to fetch data from all sources for {symbols}")

    def get_data_source_status(self) -> Dict[str, any]:
        """Get current data source status for UI display."""
        return {
            "current_source": self._current_data_source,
            "is_mock": self._using_mock_data,
            "cache_size": len(self._cache),
            "available_sources": [name for name, _ in self._data_sources]
        }

    def _validate_symbols(self, symbols: List[str]) -> None:
        """Validate symbol format."""
        if not symbols:
            raise ValidationError("No symbols provided")

        for symbol in symbols:
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValidationError(f"Invalid symbol: {symbol}")
            if len(symbol) > 10:  # Reasonable limit
                raise ValidationError(f"Symbol too long: {symbol}")

    def _get_cached_data(self, cache_key: str) -> Optional[Tuple[pd.DataFrame, bool, str]]:
        """Get data from cache if not expired."""
        if cache_key not in self._cache:
            return None

        data, timestamp, is_mock, source = self._cache[cache_key]
        if time.time() - timestamp > config.data.cache_timeout:
            del self._cache[cache_key]
            return None

        return data.copy(), is_mock, source

    def _fetch_yfinance(self, symbols: List[str], period: str) -> pd.DataFrame:
        """Fetch data using yfinance (primary source)."""
        return self._fetch_with_retries(symbols, period)

    def _fetch_alpha_vantage(self, symbols: List[str], period: str) -> pd.DataFrame:
        """Fetch data using Alpha Vantage API (secondary source)."""
        if not hasattr(config, 'alpha_vantage_key') or not config.alpha_vantage_key:
            raise DataFetchError("Alpha Vantage API key not configured")
        
        data_dict = {}
        
        for symbol in symbols:
            try:
                url = f"https://www.alphavantage.co/query"
                params = {
                    'function': 'TIME_SERIES_DAILY_ADJUSTED',
                    'symbol': symbol,
                    'apikey': config.alpha_vantage_key,
                    'outputsize': 'full'
                }
                
                response = requests.get(url, params=params, timeout=config.data.request_timeout)
                response.raise_for_status()
                json_data = response.json()
                
                if "Error Message" in json_data:
                    raise DataFetchError(f"Alpha Vantage error for {symbol}: {json_data['Error Message']}")
                
                if "Note" in json_data:
                    raise DataFetchError(f"Alpha Vantage rate limit for {symbol}")
                
                time_series = json_data.get("Time Series (Daily)", {})
                if not time_series:
                    raise DataFetchError(f"No time series data for {symbol}")
                
                # Convert to pandas format
                prices = {}
                for date_str, entry in time_series.items():
                    try:
                        date = pd.to_datetime(date_str)
                        price = float(entry["5. adjusted close"])
                        prices[date] = price
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping invalid data point for {symbol}: {e}")
                        continue
                
                if prices:
                    data_dict[symbol] = pd.Series(prices)
                    
            except Exception as e:
                logger.error(f"Failed to fetch {symbol} from Alpha Vantage: {e}")
                raise DataFetchError(f"Alpha Vantage fetch failed for {symbol}: {e}")
        
        if not data_dict:
            raise DataFetchError("No data retrieved from Alpha Vantage")
        
        # Create DataFrame and filter by period
        df = pd.DataFrame(data_dict).sort_index()
        return self._filter_by_period(df, period)

    def _filter_by_period(self, df: pd.DataFrame, period: str) -> pd.DataFrame:
        """Filter DataFrame by time period."""
        if df.empty:
            return df
            
        end_date = df.index.max()
        
        # Parse period string
        period_map = {
            '1mo': 30, '3mo': 90, '6mo': 180,
            '1y': 365, '2y': 730, '5y': 1825, '10y': 3650
        }
        
        days = period_map.get(period, 365)
        start_date = end_date - timedelta(days=days)
        
        return df[df.index >= start_date]

    def _fetch_with_retries(self, symbols: List[str], period: str) -> pd.DataFrame:
        last_error = None

        for attempt in range(config.data.max_retries):
            try:
                logger.debug(f"Fetching data attempt {attempt + 1}/{config.data.max_retries}")

                if len(symbols) == 1:
                    # Single symbol - use Ticker for better error handling
                    ticker = yf.Ticker(symbols[0])
                    hist = ticker.history(period=period)
                    if hist.empty:
                        raise DataFetchError(f"No data returned for {symbols[0]}")

                    data = pd.DataFrame({symbols[0]: hist['Close']})
                else:
                    # Multiple symbols - use download
                    data = yf.download(
                        symbols,
                        period=period,
                        progress=False,
                        auto_adjust=True,
                        timeout=config.data.request_timeout
                    )

                    if data.empty:
                        raise DataFetchError(f"No data returned for {symbols}")

                    # Extract Close prices
                    if 'Close' in data.columns.get_level_values(0):
                        data = data['Close']
                    elif len(data.columns) == len(symbols):
                        # Already flattened
                        pass
                    else:
                        raise DataFetchError("Unexpected data structure from yfinance")

                return self._clean_data(data)

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < config.data.max_retries - 1:
                    time.sleep(config.data.retry_delay * (2 ** attempt))  # Exponential backoff

        raise DataFetchError(f"Failed to fetch data after {config.data.max_retries} attempts: {last_error}")

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate fetched data."""
        # Remove rows with all NaN values
        data = data.dropna(how='all')

        if data.empty:
            raise ValidationError("All data is NaN after cleaning")

        # Forward fill missing values (common in stock data)
        data = data.ffill()

        # Drop any remaining NaN rows
        data = data.dropna()

        if data.empty:
            raise ValidationError("No valid data after cleaning")

        # Ensure positive prices
        if (data <= 0).any().any():
            logger.warning("Found non-positive prices, replacing with forward fill")
            data = data.mask(data <= 0).ffill()

        return data

    def _validate_data(self, data: pd.DataFrame, expected_symbols: List[str]) -> None:
        """Validate fetched data."""
        if data.empty:
            raise ValidationError("Data is empty")

        # Check if we have data for all requested symbols
        missing_symbols = set(expected_symbols) - set(data.columns)
        if missing_symbols:
            logger.warning(f"Missing data for symbols: {missing_symbols}")

        # Check data quality
        if len(data) < 10:  # Minimum reasonable data points
            raise ValidationError(f"Insufficient data points: {len(data)}")

        # Check for reasonable price ranges (basic sanity check)
        for symbol in data.columns:
            prices = data[symbol].dropna()
            if prices.empty:
                continue

            if prices.min() <= 0:
                raise ValidationError(f"Invalid prices for {symbol}: found non-positive values")

            # Check for extreme volatility (prices shouldn't change by more than 50% in one day)
            daily_returns = prices.pct_change().dropna()
            if (daily_returns.abs() > 0.5).any():
                logger.warning(f"Extreme volatility detected for {symbol}")

    def _generate_fallback_data(self, symbols: List[str], period: str) -> pd.DataFrame:
        """Generate realistic mock data as fallback."""
        logger.warning(f"*** GENERATING MOCK DATA *** for {symbols} - Real data fetch failed")

        # Determine number of days based on period
        days_map = {'1y': 252, '2y': 504, '5y': 1260, '10y': 2520}
        days = days_map.get(period, 1260)

        # Generate dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        dates = dates[dates.weekday < 5]  # Only weekdays

        data = {}
        for symbol in symbols:
            # Generate realistic price series using geometric Brownian motion
            np.random.seed(hash(symbol) % 2**32)  # Deterministic but symbol-specific

            initial_price = 100 + (hash(symbol) % 200)  # Price between 100-300
            returns = np.random.normal(0.0005, 0.02, len(dates))  # ~0.1% daily return, 2% volatility

            prices = [initial_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))

            data[symbol] = pd.Series(prices, index=dates[:len(prices)])

        return pd.DataFrame(data)

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()
        logger.info("Data cache cleared")


# Global data service instance
data_service = DataService()


def get_stock_data(symbols: Union[str, List[str]], period: str = None) -> Tuple[pd.DataFrame, str]:
    """Convenience function for getting stock data."""
    return data_service.get_stock_data(symbols, period)

def is_using_mock_data() -> bool:
    """Check if the data service is currently using mock data."""
    return data_service._using_mock_data

def get_data_source_status() -> Dict[str, any]:
    """Get current data source status."""
    return data_service.get_data_source_status()
