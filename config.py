"""
Configuration management for the Portfolio Application.
"""
import os
from dataclasses import dataclass
from typing import Dict, Any
import logging


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "portfolio.db"
    timeout: int = 30


@dataclass
class DataConfig:
    """Data fetching configuration."""
    default_period: str = "5y"
    cache_timeout: int = 300  # 5 minutes
    max_retries: int = 3
    retry_delay: float = 1.0
    request_timeout: int = 30


@dataclass
class StrategyConfig:
    """Strategy configuration."""
    min_weight: float = 0.05
    max_weight: float = 0.4
    bollinger_window: int = 20
    bollinger_std: float = 2.0
    ml_lookback_days: int = 252


@dataclass
class AppConfig:
    """Main application configuration."""
    debug: bool = False
    log_level: str = "INFO"
    database: DatabaseConfig = None
    data: DataConfig = None
    strategy: StrategyConfig = None
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.data is None:
            self.data = DataConfig()
        if self.strategy is None:
            self.strategy = StrategyConfig()

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables."""
        return cls(
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            database=DatabaseConfig(
                path=os.getenv('DB_PATH', 'portfolio.db'),
                timeout=int(os.getenv('DB_TIMEOUT', '30'))
            ),
            data=DataConfig(
                default_period=os.getenv('DEFAULT_PERIOD', '5y'),
                cache_timeout=int(os.getenv('CACHE_TIMEOUT', '300')),
                max_retries=int(os.getenv('MAX_RETRIES', '3')),
                retry_delay=float(os.getenv('RETRY_DELAY', '1.0')),
                request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30'))
            ),
            strategy=StrategyConfig(
                min_weight=float(os.getenv('MIN_WEIGHT', '0.05')),
                max_weight=float(os.getenv('MAX_WEIGHT', '0.4')),
                bollinger_window=int(os.getenv('BOLLINGER_WINDOW', '20')),
                bollinger_std=float(os.getenv('BOLLINGER_STD', '2.0')),
                ml_lookback_days=int(os.getenv('ML_LOOKBACK_DAYS', '252'))
            )
        )


# Global configuration instance
config = AppConfig.from_env()


def setup_logging(level: str = None) -> logging.Logger:
    """Setup application logging."""
    log_level = level or config.log_level
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('portfolio_app.log')
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('yfinance').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)