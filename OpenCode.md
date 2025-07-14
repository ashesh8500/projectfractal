# OpenCode Configuration - Production Portfolio App

## Quick Start
- **Setup & Run**: `source /opt/homebrew/anaconda3/etc/profile.d/conda.sh && conda activate py313_base && python setup.py`
- **Run App**: `source /opt/homebrew/anaconda3/etc/profile.d/conda.sh && conda activate py313_base && streamlit run main.py`
- **Run Tests**: `source /opt/homebrew/anaconda3/etc/profile.d/conda.sh && conda activate py313_base && python test_production.py`

## Production Architecture
- **Entry Point**: `main.py` (Streamlit app)
- **Core Modules**: `portfolio_manager.py`, `strategies.py`, `data_service.py`, `database.py`
- **Configuration**: `config.py` (environment-based config)
- **Error Handling**: `exceptions.py` (custom exception hierarchy)

## Code Style Guidelines
- **Logging**: Use `logging` module, not print statements
- **Error Handling**: Custom exceptions with proper error chains (`raise ... from e`)
- **Type Hints**: Full typing with `from typing import Dict, List, Optional`
- **Validation**: Input validation in all public methods
- **Documentation**: Docstrings with Args/Returns/Raises sections
- **Configuration**: Environment variables via `config.py`, no hardcoded values

## Key Patterns
- **Dependency Injection**: Pass services/config to constructors
- **Context Managers**: Database operations use `with` statements
- **Thread Safety**: Database manager uses thread-local connections
- **Caching**: Data service implements LRU cache with TTL
- **Fallback Systems**: Mock data generation when external APIs fail
- **Strategy Pattern**: Abstract base class for rebalancing strategies

## Troubleshooting
- **Database Schema Errors**: If you encounter `no such column` or other schema-related errors, the simplest fix is to delete the `portfolio.db` file and restart the application. The database will be recreated with the correct schema.
- **`JSONEncodeError`**: This error indicates a problem with the data being saved to the database. Ensure that all data being saved is JSON serializable.
- **`yfinance` errors**: If you see errors from `yfinance`, it's likely due to an invalid ticker symbol. The application will fall back to mock data in this case.