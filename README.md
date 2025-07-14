# Portfolio Optimizer Pro

A production-grade portfolio management and optimization application built with Streamlit, featuring AI-powered rebalancing strategies and comprehensive analytics.

## Features

### 🚀 Core Functionality
- **Real-time Portfolio Tracking**: Live portfolio valuation and performance metrics
- **AI-Powered Strategies**: Bollinger Bands and Machine Learning rebalancing algorithms
- **Data Persistence**: SQLite database with full portfolio history tracking
- **Robust Data Fetching**: Multi-source data with intelligent fallbacks and caching

### 📊 Analytics & Visualization
- Interactive portfolio composition charts
- Performance metrics (Sharpe ratio, volatility, returns)
- Historical price analysis and normalized performance comparison
- Strategy comparison and implementation suggestions

### 🛡️ Production Features
- Comprehensive error handling and logging
- Environment-based configuration management
- Thread-safe database operations
- Input validation and data sanitization
- Automated testing suite

## Quick Start

### Prerequisites
- Python 3.8+ (tested with Python 3.13)
- Conda environment `py313_base` (or modify commands accordingly)

### Installation & Setup

1. **Clone and navigate to the project**:
   ```bash
   cd "/Users/asheshkaji/Documents/University Files/Learning code/Stock Portfolio Project/portfolio_app"
   ```

2. **Activate conda environment and run setup**:
   ```bash
   source /opt/homebrew/anaconda3/etc/profile.d/conda.sh && conda activate py313_base && python setup.py
   ```

3. **Follow the interactive setup**:
   - Choose option 3 to run tests and start the application
   - The setup will install dependencies and create configuration files

### Manual Setup (Alternative)

1. **Install dependencies**:
   ```bash
   pip install -r requirements_production.txt
   ```

2. **Run tests**:
   ```bash
   python test_production.py
   ```

3. **Start the application**:
   ```bash
   streamlit run main.py
   ```

## Usage

### Creating Your First Portfolio

1. **Launch the application** and navigate to `http://localhost:8501`
2. **Create a new portfolio** in the sidebar:
   - Enter a portfolio name
   - Add stock symbols (one per line): `AAPL`, `MSFT`, `GOOGL`
   - Add corresponding shares: `100`, `50`, `25`
   - Click "Create Portfolio"

3. **Explore your portfolio**:
   - View current value and composition
   - Analyze performance metrics
   - Examine price charts and trends

### Running Rebalancing Strategies

1. **Select a strategy** from the sidebar dropdown:
   - **Bollinger Bands**: Mean reversion strategy using statistical bands
   - **ML Strategy**: Machine learning-based return predictions

2. **Click "Run Strategy"** to see:
   - Current vs. recommended weights
   - Implementation suggestions (buy/sell recommendations)
   - Expected impact on portfolio allocation

### Managing Portfolios

- **Save portfolios** to database for persistence
- **Load existing portfolios** from the dropdown
- **Refresh data** to get latest market prices
- **View portfolio history** and track changes over time

## Architecture

### Core Components

```
├── main.py                 # Streamlit application entry point
├── config.py              # Environment-based configuration
├── exceptions.py          # Custom exception hierarchy
├── data_service.py        # Robust data fetching with caching
├── portfolio_manager.py   # Portfolio operations and calculations
├── strategies.py          # Rebalancing strategy implementations
├── database.py           # Thread-safe database operations
└── test_production.py    # Comprehensive test suite
```

### Key Design Patterns

- **Strategy Pattern**: Pluggable rebalancing algorithms
- **Dependency Injection**: Configurable services and components
- **Repository Pattern**: Database abstraction layer
- **Observer Pattern**: Real-time data updates
- **Factory Pattern**: Strategy creation and management

## Configuration

The application uses environment-based configuration via `.env` file:

```env
# Application Settings
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
DB_PATH=portfolio.db
DB_TIMEOUT=30

# Data Fetching
DEFAULT_PERIOD=5y
CACHE_TIMEOUT=300
MAX_RETRIES=3

# Strategy Parameters
MIN_WEIGHT=0.05
MAX_WEIGHT=0.4
BOLLINGER_WINDOW=20
```

## Testing

### Running Tests

```bash
# Run full test suite
python test_production.py

# Run with pytest (if installed)
pytest test_production.py -v

# Run specific test class
python -c "from test_production import TestPortfolioManager; import unittest; unittest.main(module=None, argv=[''], testRunner=unittest.TextTestRunner(verbosity=2), exit=False, testLoader=unittest.TestLoader().loadTestsFromTestCase(TestPortfolioManager))"
```

### Test Coverage

- **Data Service**: API integration, caching, fallback mechanisms
- **Portfolio Manager**: Calculations, validation, position management
- **Strategies**: Algorithm correctness, edge cases, weight constraints
- **Database**: CRUD operations, concurrency, data integrity
- **Configuration**: Environment loading, validation

## Logging

The application provides comprehensive logging:

- **Application logs**: `portfolio_app.log`
- **Console output**: Real-time status and errors
- **Log levels**: DEBUG, INFO, WARNING, ERROR
- **Structured logging**: Timestamps, modules, and context

## Error Handling

### Graceful Degradation
- **Network failures**: Automatic fallback to mock data
- **API rate limits**: Exponential backoff and retry logic
- **Data quality issues**: Validation and cleaning
- **User input errors**: Clear error messages and suggestions

### Custom Exceptions
- `DataFetchError`: Data retrieval failures
- `StrategyError`: Algorithm calculation issues
- `ValidationError`: Input validation failures
- `DatabaseError`: Persistence layer problems

## Performance Considerations

### Optimization Features
- **Data caching**: 5-minute TTL for market data
- **Database connection pooling**: Thread-local connections
- **Lazy loading**: On-demand data fetching
- **Efficient algorithms**: Vectorized calculations with pandas/numpy

### Scalability
- **Stateless design**: Easy horizontal scaling
- **Database abstraction**: Simple migration to PostgreSQL/MySQL
- **Modular architecture**: Independent service scaling
- **Configuration management**: Environment-specific settings

## Development

### Adding New Strategies

1. **Inherit from BaseStrategy**:
   ```python
   class MyStrategy(BaseStrategy):
       def calculate_new_weights(self, prices, current_weights):
           # Implementation here
           return new_weights
   ```

2. **Register in strategies.py**:
   ```python
   STRATEGIES['my_strategy'] = MyStrategy
   ```

3. **Add tests** in `test_production.py`

### Extending Data Sources

1. **Implement data fetcher** in `data_service.py`
2. **Add fallback mechanisms** for reliability
3. **Update configuration** for new parameters
4. **Add comprehensive tests**

## Troubleshooting

### Common Issues

**"Module not found" errors**:
- Ensure conda environment is activated
- Run `pip install -r requirements_production.txt`

**Database locked errors**:
- Close other application instances
- Delete `portfolio.db` to reset (loses data)

**Network/API failures**:
- Check internet connection
- Application will use fallback mock data automatically

**Performance issues**:
- Clear data cache: restart application
- Reduce data period in configuration
- Check system resources

### Debug Mode

Enable debug logging by setting `DEBUG=true` in `.env` file or:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
streamlit run main.py
```

## Contributing

### Code Style
- Follow PEP 8 guidelines
- Use type hints for all functions
- Add comprehensive docstrings
- Include error handling and logging
- Write tests for new features

### Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation
6. Submit pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the comprehensive test suite for examples
- Examine the logging output for detailed error information