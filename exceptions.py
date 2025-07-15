"""
Custom exceptions for the Portfolio Application.
"""


class PortfolioError(Exception):
    """Base exception for portfolio-related errors."""
    pass


class DataFetchError(PortfolioError):
    """Raised when data fetching fails."""
    pass


class StrategyError(PortfolioError):
    """Raised when strategy calculation fails."""
    pass


class DatabaseError(PortfolioError):
    """Raised when database operations fail."""
    pass


class ValidationError(PortfolioError):
    """Raised when data validation fails."""
    pass


class ConfigurationError(PortfolioError):
    """Raised when configuration is invalid."""
    pass


class AuthenticationError(PortfolioError):
    """Raised when authentication fails."""
    pass