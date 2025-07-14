"""
Robust data fetcher with multiple fallback mechanisms.
Handles yfinance issues and provides realistic mock data when needed.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import time
import random

class DataFetcher:
    """Robust data fetcher with multiple fallback strategies."""

    def __init__(self):
        self.cache = {}

    def fetch_stock_data(self, symbols: Union[str, List[str]], period: str = '5y') -> pd.DataFrame:
        """
        Fetch stock data with robust error handling and fallbacks.

        Args:
            symbols: Single symbol string or list of symbols
            period: Time period ('1y', '2y', '5y', etc.)

        Returns:
            DataFrame with Close prices for each symbol
        """
        if isinstance(symbols, str):
            symbols = [symbols]

        # Try multiple approaches in order of preference
        data = None

        # Approach 1: Standard yfinance download
        data = self._try_yfinance_download(symbols, period)

        # Approach 2: Individual ticker approach
        if data is None or data.empty:
            data = self._try_individual_tickers(symbols, period)

        # Approach 3: Alternative yfinance settings
        if data is None or data.empty:
            data = self._try_alternative_settings(symbols, period)

        # Approach 4: Generate realistic mock data
        if data is None or data.empty:
            print(f"⚠️  All data fetching methods failed for {symbols}. Using realistic mock data.")
            data = self._generate_realistic_mock_data(symbols, period)

        return data

    def _try_yfinance_download(self, symbols: List[str], period: str) -> Optional[pd.DataFrame]:
        """Try standard yfinance download."""
        symbols = [symbol.replace("'",'"') for symbol in symbols]
        try:
            print(f"📡 Attempting yfinance download for {symbols} (period: {period})")

            # Add delay to avoid rate limiting
            time.sleep(0.2)

            if len(symbols) == 1:
                data = yf.download(symbols[0], period=period, progress=False,
                                 timeout=15, threads=False)
                if not data.empty and 'Close' in data.columns:
                    result = pd.DataFrame({symbols[0]: data['Close']})
                    print(f"✅ Successfully fetched data for {symbols[0]}: {len(result)} days")
                    return result
            else:
                data = yf.download(symbols, period=period, progress=False,
                                 timeout=15, threads=False)
                if not data.empty:
                    if 'Close' in data.columns:
                        if isinstance(data['Close'], pd.DataFrame):
                            result = data['Close']
                        else:
                            result = pd.DataFrame({symbols[0]: data['Close']})
                        print(f"✅ Successfully fetched data for {symbols}: {len(result)} days")
                        return result

        except Exception as e:
            print(f"❌ yfinance download failed: {e}")

        return None

    def _try_individual_tickers(self, symbols: List[str], period: str) -> Optional[pd.DataFrame]:
        """Try fetching each ticker individually."""
        try:
            print(f"🔄 Trying individual ticker approach for {symbols}")

            results = {}
            for symbol in symbols:
                try:
                    time.sleep(0.1)  # Small delay between requests
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period=period)

                    if not hist.empty and 'Close' in hist.columns:
                        results[symbol] = hist['Close']
                        print(f"✅ Got data for {symbol}: {len(hist)} days")
                    else:
                        print(f"❌ No data for {symbol}")

                except Exception as e:
                    print(f"❌ Failed to fetch {symbol}: {e}")
                    continue

            if results:
                data = pd.DataFrame(results)
                # Align all series to common dates
                data = data.dropna()
                return data

        except Exception as e:
            print(f"❌ Individual ticker approach failed: {e}")

        return None

    def _try_alternative_settings(self, symbols: List[str], period: str) -> Optional[pd.DataFrame]:
        """Try with alternative yfinance settings."""
        try:
            print(f"🔧 Trying alternative settings for {symbols}")

            # Try with different intervals and settings
            settings_to_try = [
                {'interval': '1d', 'prepost': True, 'auto_adjust': True},
                {'interval': '1d', 'prepost': False, 'auto_adjust': False},
                {'interval': '5d', 'prepost': True, 'auto_adjust': True},
            ]

            for settings in settings_to_try:
                try:
                    time.sleep(0.3)
                    data = yf.download(symbols, period=period, progress=False,
                                     timeout=20, **settings)

                    if not data.empty and 'Close' in data.columns:
                        if isinstance(data['Close'], pd.DataFrame):
                            result = data['Close']
                        else:
                            result = pd.DataFrame({symbols[0]: data['Close']})

                        if not result.empty:
                            print(f"✅ Alternative settings worked: {len(result)} days")
                            return result

                except Exception as e:
                    continue

        except Exception as e:
            print(f"❌ Alternative settings failed: {e}")

        return None

    def _generate_realistic_mock_data(self, symbols: List[str], period: str) -> pd.DataFrame:
        """Generate realistic mock stock data based on historical patterns."""

        # Parse period to get number of days
        period_days = self._parse_period_to_days(period)

        # Create date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')

        # Filter to business days only
        dates = dates[dates.weekday < 5]

        data = {}

        # Realistic starting prices for common stocks
        realistic_prices = {
            'AAPL': 180.0, 'MSFT': 350.0, 'GOOGL': 2500.0, 'AMZN': 3200.0,
            'TSLA': 800.0, 'NVDA': 900.0, 'META': 400.0, 'NFLX': 450.0,
            'SPY': 450.0, 'QQQ': 380.0, 'VTI': 220.0, 'BND': 75.0
        }

        for symbol in symbols:
            # Set realistic starting price
            start_price = realistic_prices.get(symbol, 100.0)

            # Generate realistic price movement
            # Stock prices follow geometric Brownian motion with some mean reversion
            n_days = len(dates)

            # Parameters for realistic stock movement
            annual_return = 0.08  # 8% annual return
            annual_volatility = 0.25  # 25% annual volatility
            mean_reversion_strength = 0.1

            # Daily parameters
            dt = 1/252  # Daily time step (252 trading days per year)
            daily_drift = annual_return * dt
            daily_vol = annual_volatility * np.sqrt(dt)

            # Generate price series
            prices = np.zeros(n_days)
            prices[0] = start_price

            np.random.seed(hash(symbol) % 2**32)  # Deterministic but symbol-specific

            for i in range(1, n_days):
                # Mean reversion component
                log_price = np.log(prices[i-1])
                log_mean = np.log(start_price)
                mean_reversion = -mean_reversion_strength * (log_price - log_mean) * dt

                # Random shock
                shock = np.random.normal(0, daily_vol)

                # Update price
                log_return = daily_drift + mean_reversion + shock
                prices[i] = prices[i-1] * np.exp(log_return)

                # Add some occasional larger moves (earnings, news, etc.)
                if np.random.random() < 0.02:  # 2% chance per day
                    jump = np.random.normal(0, 0.05)  # 5% jump
                    prices[i] *= (1 + jump)

            # Ensure prices are positive
            prices = np.maximum(prices, start_price * 0.1)

            data[symbol] = pd.Series(prices, index=dates)

        result = pd.DataFrame(data)
        print(f"🎯 Generated realistic mock data for {symbols}: {len(result)} days")
        return result

    def _parse_period_to_days(self, period: str) -> int:
        """Parse period string to number of days."""
        period = period.lower()

        if period.endswith('d'):
            return int(period[:-1])
        elif period.endswith('mo'):
            return int(period[:-2]) * 30
        elif period.endswith('y'):
            return int(period[:-1]) * 365
        else:
            # Default mappings
            mappings = {
                '1y': 365, '2y': 730, '3y': 1095, '5y': 1825, '10y': 3650,
                '1mo': 30, '3mo': 90, '6mo': 180,
                'ytd': 250, 'max': 3650
            }
            return mappings.get(period, 365)

# Global instance
data_fetcher = DataFetcher()

def get_stock_data(symbols: Union[str, List[str]], period: str = '5y') -> pd.DataFrame:
    """Convenience function to fetch stock data."""
    return data_fetcher.fetch_stock_data(symbols, period)
