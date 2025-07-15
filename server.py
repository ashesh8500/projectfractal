#!/usr/bin/env python3
"""
gRPC server for the Portfolio Application.
"""
import grpc
from concurrent import futures
import logging
from typing import Dict

# Generated from proto
import portfolio_pb2
import portfolio_pb2_grpc

from config import setup_logging
from portfolio_manager import PortfolioManager
from strategies import get_strategy
from database import db_manager
from exceptions import PortfolioError, ValidationError, DatabaseError
from data_service import DataService
from auth import auth_manager
from backtesting import PortfolioBacktester, create_monthly_allocation_data

logger = setup_logging()

class PortfolioServicer(portfolio_pb2_grpc.PortfolioServiceServicer):
    """gRPC servicer for portfolio operations."""

    def __init__(self):
        self.data_service = DataService()
    
    def Authenticate(self, request, context):
        """Authenticate a user and create a session."""
        try:
            user_info = auth_manager.authenticate(request.username, request.password)
            
            if user_info:
                return portfolio_pb2.AuthResponse(
                    success=True,
                    message="Authentication successful",
                    user=portfolio_pb2.User(
                        user_id=user_info['user_id'],
                        username=user_info['username'],
                        email=user_info['email'] or ""
                    ),
                    session_token=user_info['session_token']
                )
            else:
                return portfolio_pb2.AuthResponse(
                    success=False,
                    message="Invalid username or password",
                    user=None,
                    session_token=""
                )
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return portfolio_pb2.AuthResponse(
                success=False,
                message="Authentication error",
                user=None,
                session_token=""
            )
    
    def ListPortfolios(self, request, context):
        """List all portfolios for a user."""
        try:
            if not request.user_id:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "User ID is required")
            
            portfolios = db_manager.list_portfolios(request.user_id)
            
            return portfolio_pb2.ListPortfoliosResponse(
                portfolio_names=portfolios
            )
        except Exception as e:
            logger.error(f"ListPortfolios failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, "Internal server error")

    def CreatePortfolio(self, request, context):
        """Create a new portfolio."""
        try:
            if not request.user_id:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "User ID is required")
            
            holdings_dict: Dict[str, float] = dict(request.holdings.shares)
            if not holdings_dict:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Holdings cannot be empty")

            # Validate holdings
            for symbol, shares in holdings_dict.items():
                if not isinstance(symbol, str) or not symbol.strip():
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Invalid symbol: {symbol}")
                if shares <= 0:
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Shares must be positive: {shares}")

            # Create portfolio manager to validate and get current data
            pm = PortfolioManager(holdings_dict)
            summary = pm.get_summary()

            # Save to database
            db_manager.save_portfolio(request.user_id, request.name, holdings_dict)

            logger.info(f"Created portfolio '{request.name}' with {len(holdings_dict)} holdings")

            return portfolio_pb2.Portfolio(
                name=request.name,
                holdings=portfolio_pb2.Holdings(shares=holdings_dict),
                total_value=summary['total_value'],
                weights=summary['weights'],
                is_using_mock_data=summary['is_using_mock_data']
            )
        except ValidationError as e:
            logger.error(f"Validation error in CreatePortfolio: {e}")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except DatabaseError as e:
            logger.error(f"Database error in CreatePortfolio: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        except Exception as e:
            logger.error(f"CreatePortfolio failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, "Internal server error")

    def LoadPortfolio(self, request, context):
        """Load an existing portfolio."""
        try:
            if not request.user_id:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "User ID is required")
            if not request.name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Portfolio name cannot be empty")

            holdings = db_manager.load_portfolio(request.user_id, request.name)
            if holdings is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Portfolio '{request.name}' not found")

            pm = PortfolioManager(holdings)
            summary = pm.get_summary()

            logger.info(f"Loaded portfolio '{request.name}' with {len(holdings)} holdings")

            return portfolio_pb2.Portfolio(
                name=request.name,
                holdings=portfolio_pb2.Holdings(shares=holdings),
                total_value=summary['total_value'],
                weights=summary['weights'],
                is_using_mock_data=summary['is_using_mock_data']
            )
        except DatabaseError as e:
            logger.error(f"Database error in LoadPortfolio: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        except Exception as e:
            logger.error(f"LoadPortfolio failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, "Internal server error")

    def RunStrategy(self, request, context):
        """Run a rebalancing strategy."""
        try:
            if not request.user_id:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "User ID is required")
            if not request.portfolio_name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Portfolio name cannot be empty")
            if not request.strategy_name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Strategy name cannot be empty")

            # Load portfolio
            holdings = db_manager.load_portfolio(request.user_id, request.portfolio_name)
            if holdings is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Portfolio '{request.portfolio_name}' not found")

            # Create portfolio manager
            logger.debug(f"Creating portfolio manager with holdings: {holdings}")
            pm = PortfolioManager(holdings)
            
            logger.debug("Getting price history...")
            prices = pm.get_price_history()
            logger.debug(f"Price history shape: {prices.shape if hasattr(prices, 'shape') else 'N/A'}")
            
            logger.debug("Getting current weights...")
            current_weights = pm.get_current_weights()
            logger.debug(f"Current weights: {current_weights}")

            # Convert strategy parameters
            params_dict: Dict[str, str] = dict(request.params.params) if request.params else {}
            converted_params = {}
            for k, v in params_dict.items():
                try:
                    # Try to convert to appropriate type
                    if '.' in v:
                        converted_params[k] = float(v)
                    else:
                        converted_params[k] = int(v)
                except ValueError:
                    converted_params[k] = v

            # Run strategy
            strategy = get_strategy(request.strategy_name, **converted_params)
            new_weights = strategy.calculate_new_weights(prices, current_weights)

            # Calculate changes
            changes = {s: new_weights.get(s, 0.0) - current_weights[s] for s in current_weights}

            # Log strategy execution
            logger.info(f"Executed strategy '{request.strategy_name}' on portfolio '{request.portfolio_name}' with params {converted_params}")

            return portfolio_pb2.StrategyResult(
                new_weights=new_weights,
                changes=changes,
                is_using_mock_data=pm.is_using_mock_data
            )
        except ValidationError as e:
            logger.error(f"Validation error in RunStrategy: {e}")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except PortfolioError as e:
            logger.error(f"Portfolio error in RunStrategy: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        except Exception as e:
            import traceback
            logger.error(f"RunStrategy failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            context.abort(grpc.StatusCode.INTERNAL, f"Strategy execution failed: {str(e)}")

    def GetPriceHistory(self, request, context):
        """Get price history for a portfolio or ticker list."""
        try:
            if not request.user_id:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "User ID is required")
            if not request.portfolio_name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Portfolio name cannot be empty")

            # Check if this is a ticker list request (format: TICKERS_SYMBOL1_SYMBOL2_...)
            if request.portfolio_name.startswith("TICKERS_"):
                # Extract ticker symbols from the request
                ticker_part = request.portfolio_name[8:]  # Remove "TICKERS_" prefix
                symbols = ticker_part.split("_")
                logger.info(f"GetPriceHistory for tickers: {symbols}")
                
                # Create a temporary holdings dict for the tickers
                holdings = {symbol: 100.0 for symbol in symbols}  # Use 100 shares as default
            else:
                # Load portfolio to get symbols
                holdings = db_manager.load_portfolio(request.user_id, request.portfolio_name)
                if holdings is None:
                    context.abort(grpc.StatusCode.NOT_FOUND, f"Portfolio '{request.portfolio_name}' not found")

            # Get price history
            pm = PortfolioManager(holdings)
            prices = pm.get_price_history()

            if prices.empty:
                context.abort(grpc.StatusCode.INTERNAL, "No price data available")

            # Flatten prices for proto transmission
            # Client needs to reshape: for each symbol, slice prices[i*rows:(i+1)*rows] where rows = len(prices)/len(symbols)
            symbols = list(prices.columns)
            all_prices = []
            
            # Fill NaN values with forward fill, then backward fill (using new pandas syntax)
            prices_filled = prices.ffill().bfill()
            
            for symbol in symbols:
                symbol_prices = prices_filled[symbol].tolist()
                all_prices.extend(symbol_prices)

            logger.info(f"Retrieved price history for '{request.portfolio_name}': {len(symbols)} symbols, {len(prices)} data points")

            return portfolio_pb2.PriceHistory(
                symbols=symbols,
                prices=all_prices,
                is_using_mock_data=pm.is_using_mock_data
            )
        except Exception as e:
            logger.error(f"GetPriceHistory failed: {e}")
            import traceback
            logger.error(f"GetPriceHistory traceback: {traceback.format_exc()}")
            context.abort(grpc.StatusCode.INTERNAL, "Internal server error")

    def RunBacktest(self, request, context):
        """Run a comprehensive backtest on a strategy."""
        try:
            if not request.user_id:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "User ID is required")
            if not request.portfolio_name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Portfolio name cannot be empty")
            if not request.strategy_name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Strategy name cannot be empty")

            # Load portfolio
            holdings = db_manager.load_portfolio(request.user_id, request.portfolio_name)
            if holdings is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Portfolio '{request.portfolio_name}' not found")

            # Create portfolio manager and get price data
            pm = PortfolioManager(holdings)
            prices = pm.get_price_history()
            
            if prices.empty:
                context.abort(grpc.StatusCode.INTERNAL, "No price data available for backtesting")

            # Convert strategy parameters
            params_dict: Dict[str, str] = dict(request.params.params) if request.params else {}
            converted_params = {}
            for k, v in params_dict.items():
                try:
                    if '.' in v:
                        converted_params[k] = float(v)
                    else:
                        converted_params[k] = int(v)
                except ValueError:
                    converted_params[k] = v

            # Get strategy and calculate weights
            strategy = get_strategy(request.strategy_name, **converted_params)
            current_weights = pm.get_current_weights()
            strategy_weights = strategy.calculate_new_weights(prices, current_weights)

            # Run backtest
            backtester = PortfolioBacktester(prices)
            backtest_results = backtester.run_backtest(
                strategy_weights=strategy_weights,
                rebalance_frequency=request.rebalance_frequency or 'M',
                start_value=request.start_value or 100.0,
                transaction_cost=request.transaction_cost or 0.001
            )

            # Prepare allocation data for visualization
            monthly_allocations = create_monthly_allocation_data(backtest_results.allocations)
            allocation_dates = []
            allocations = []
            
            if not monthly_allocations.empty:
                for date, row in monthly_allocations.iterrows():
                    allocation_dates.append(date.strftime('%Y-%m-%d'))
                    weights = {}
                    for symbol in prices.columns:
                        weights[symbol] = row.get(symbol, 0.0)
                    allocations.append(portfolio_pb2.AllocationSnapshot(
                        date=date.strftime('%Y-%m-%d'),
                        weights=weights
                    ))

            # Convert timedelta to days for gRPC
            avg_winning_duration_days = int(backtest_results.avg_winning_trade_duration.total_seconds() / 86400)
            avg_losing_duration_days = int(backtest_results.avg_losing_trade_duration.total_seconds() / 86400)
            max_dd_duration_days = int(backtest_results.max_drawdown_duration.total_seconds() / 86400)

            logger.info(f"Completed backtest for '{request.portfolio_name}' using '{request.strategy_name}' strategy: "
                       f"{backtest_results.total_return_pct:.2f}% return, {len(backtest_results.trades)} trades")

            return portfolio_pb2.BacktestResult(
                # Period info
                start_date=backtest_results.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                end_date=backtest_results.end_date.strftime('%Y-%m-%d %H:%M:%S'),
                period_days=backtest_results.period.days,
                
                # Performance metrics
                start_value=backtest_results.start_value,
                end_value=backtest_results.end_value,
                total_return_pct=backtest_results.total_return_pct,
                benchmark_return_pct=backtest_results.benchmark_return_pct,
                max_gross_exposure_pct=backtest_results.max_gross_exposure_pct,
                total_fees_paid=backtest_results.fees,
                
                # Drawdown analysis
                max_drawdown_pct=backtest_results.max_drawdown_pct,
                max_drawdown_duration_days=max_dd_duration_days,
                
                # Trade analysis
                total_trades=backtest_results.total_trades,
                total_closed_trades=backtest_results.total_closed_trades,
                total_open_trades=backtest_results.total_open_trades,
                open_trade_pnl=backtest_results.open_trade_pnl,
                win_rate_pct=backtest_results.win_rate_pct,
                best_trade_pct=backtest_results.best_trade_pct,
                worst_trade_pct=backtest_results.worst_trade_pct,
                avg_winning_trade_pct=backtest_results.avg_winning_trade_pct,
                avg_losing_trade_pct=backtest_results.avg_losing_trade_pct,
                avg_winning_trade_duration_days=avg_winning_duration_days,
                avg_losing_trade_duration_days=avg_losing_duration_days,
                profit_factor=backtest_results.profit_factor,
                expectancy=backtest_results.expectancy,
                
                # Risk metrics
                sharpe_ratio=backtest_results.sharpe_ratio,
                calmar_ratio=backtest_results.calmar_ratio,
                omega_ratio=backtest_results.omega_ratio,
                sortino_ratio=backtest_results.sortino_ratio,
                
                # Allocation data
                allocation_dates=allocation_dates,
                allocations=allocations,
                
                is_using_mock_data=pm.is_using_mock_data
            )
            
        except ValidationError as e:
            logger.error(f"Validation error in RunBacktest: {e}")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except PortfolioError as e:
            logger.error(f"Portfolio error in RunBacktest: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        except Exception as e:
            import traceback
            logger.error(f"RunBacktest failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            context.abort(grpc.StatusCode.INTERNAL, f"Backtest execution failed: {str(e)}")

import os

def serve():
    """Start the gRPC server."""
    port = os.environ.get('PORT', '50051')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    portfolio_pb2_grpc.add_PortfolioServiceServicer_to_server(PortfolioServicer(), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logger.info(f"gRPC server started on port {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        server.stop(0)

if __name__ == '__main__':
    serve()