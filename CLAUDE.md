# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Dependencies
```bash
# Full setup with conda environment
source /opt/homebrew/anaconda3/etc/profile.d/conda.sh && conda activate py313_base && python setup.py

# Install dependencies only
pip install -r requirements_production.txt

# Create default .env configuration
python setup.py
```

### Running the Application
```bash
# Start the Streamlit application
streamlit run main.py

# Start with specific port/address
streamlit run main.py --server.port 8501 --server.address localhost
```

### Testing
```bash
# Run full test suite
python test_production.py

# Run with pytest (if installed)
pytest test_production.py -v

# Run specific test class
python -c "from test_production import TestPortfolioManager; import unittest; unittest.main(module=None, argv=[''], testRunner=unittest.TextTestRunner(verbosity=2), exit=False, testLoader=unittest.TestLoader().loadTestsFromTestCase(TestPortfolioManager))"
```

### Code Quality
```bash
# Format code with black
black *.py

# Lint with flake8
flake8 *.py

# Type checking with mypy
mypy *.py
```

## Architecture Overview

This is a production-grade portfolio management application built with Streamlit that implements AI-powered rebalancing strategies.

### Core Components Architecture

```
├── main.py                 # Streamlit UI application entry point
├── config.py              # Environment-based configuration management
├── exceptions.py          # Custom exception hierarchy
├── data_service.py        # Robust data fetching with caching and fallbacks
├── portfolio_manager.py   # Portfolio calculations and validation
├── strategies.py          # Strategy pattern implementation for rebalancing
├── database.py           # Thread-safe SQLite database operations
└── test_production.py    # Comprehensive test suite
```

### Key Design Patterns

- **Strategy Pattern**: `BaseStrategy` abstract class with pluggable implementations (`BollingerBandsStrategy`, `MLStrategy`)
- **Repository Pattern**: `DatabaseManager` abstracts database operations
- **Dependency Injection**: Configuration passed through `config` object
- **Factory Pattern**: `get_strategy()` function for strategy creation
- **Observer Pattern**: Real-time data updates through Streamlit state management

### Configuration System

The application uses a hierarchical configuration system:
- Environment variables (`.env` file)
- `AppConfig` dataclass with nested configs (`DatabaseConfig`, `DataConfig`, `StrategyConfig`)
- Default values with environment overrides
- Type-safe configuration access through `config` global instance

### Data Flow

1. **UI Layer** (`main.py`): Streamlit interface handling user interactions
2. **Business Logic** (`portfolio_manager.py`): Portfolio calculations and validation
3. **Strategy Layer** (`strategies.py`): Rebalancing algorithm implementations
4. **Data Layer** (`data_service.py`): Stock data fetching with caching
5. **Persistence** (`database.py`): Thread-safe portfolio storage

### Error Handling Strategy

Custom exception hierarchy with graceful degradation:
- `PortfolioError`: Base exception
- `DataFetchError`: Network/API failures → Falls back to mock data
- `StrategyError`: Algorithm failures → Returns current weights
- `ValidationError`: Input validation → Clear user feedback
- `DatabaseError`: Persistence failures → Memory-only operation

### Testing Architecture

Comprehensive test suite (`test_production.py`) covering:
- Unit tests for all core components
- Integration tests for data flow
- Mock data for offline testing
- Strategy validation and edge cases
- Database concurrency testing

### Key Implementation Details

- **Thread Safety**: Database operations use thread-local connections
- **Caching**: 5-minute TTL for market data with LRU cache
- **Fallback Mechanisms**: Mock data when real APIs fail
- **Type Safety**: Comprehensive type hints throughout codebase
- **Logging**: Structured logging with configurable levels
- **Input Validation**: Robust validation at all entry points

## Development Workflow

1. **Environment Setup**: Use `python setup.py` for initial setup
2. **Configuration**: Modify `.env` file for environment-specific settings
3. **Testing**: Always run `python test_production.py` before changes
4. **Code Quality**: Use black, flake8, and mypy for code quality
5. **Database**: SQLite file `portfolio.db` is created automatically

## Strategy Development

To add new rebalancing strategies:

1. Inherit from `BaseStrategy` class in `strategies.py`
2. Implement `calculate_new_weights()` method
3. Add strategy to `STRATEGIES` dictionary
4. Include comprehensive tests in `test_production.py`
5. Update strategy configuration in `config.py` if needed

## Database Schema

The application uses SQLite with the following key tables:
- `portfolios`: Portfolio metadata and holdings
- `strategy_results`: Historical strategy execution results
- Thread-safe operations with proper connection management