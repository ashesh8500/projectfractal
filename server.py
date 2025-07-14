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

logger = setup_logging()

class PortfolioServicer(portfolio_pb2_grpc.PortfolioServiceServicer):
    """gRPC servicer for portfolio operations."""

    def __init__(self):
        self.user_id = "default_user"  # Fixed for simplicity; extend for multi-user
        self.data_service = DataService()

    def CreatePortfolio(self, request, context):
        """Create a new portfolio."""
        try:
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
            db_manager.save_portfolio(self.user_id, request.name, holdings_dict)

            logger.info(f"Created portfolio '{request.name}' with {len(holdings_dict)} holdings")

            return portfolio_pb2.Portfolio(
                name=request.name,
                holdings=portfolio_pb2.Holdings(shares=holdings_dict),
                total_value=summary['total_value'],
                weights=summary['weights']
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
            if not request.name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Portfolio name cannot be empty")

            holdings = db_manager.load_portfolio(self.user_id, request.name)
            if holdings is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Portfolio '{request.name}' not found")

            pm = PortfolioManager(holdings)
            summary = pm.get_summary()

            logger.info(f"Loaded portfolio '{request.name}' with {len(holdings)} holdings")

            return portfolio_pb2.Portfolio(
                name=request.name,
                holdings=portfolio_pb2.Holdings(shares=holdings),
                total_value=summary['total_value'],
                weights=summary['weights']
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
            if not request.portfolio_name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Portfolio name cannot be empty")
            if not request.strategy_name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Strategy name cannot be empty")

            # Load portfolio
            holdings = db_manager.load_portfolio(self.user_id, request.portfolio_name)
            if holdings is None:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Portfolio '{request.portfolio_name}' not found")

            # Create portfolio manager
            pm = PortfolioManager(holdings)
            prices = pm.get_price_history()
            current_weights = pm.get_current_weights()

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
                changes=changes
            )
        except ValidationError as e:
            logger.error(f"Validation error in RunStrategy: {e}")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except PortfolioError as e:
            logger.error(f"Portfolio error in RunStrategy: {e}")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
        except Exception as e:
            logger.error(f"RunStrategy failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, "Internal server error")

    def GetPriceHistory(self, request, context):
        """Get price history for a portfolio."""
        try:
            if not request.portfolio_name.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Portfolio name cannot be empty")

            # Load portfolio to get symbols
            holdings = db_manager.load_portfolio(self.user_id, request.portfolio_name)
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
            
            # Fill NaN values with forward fill, then backward fill
            prices_filled = prices.fillna(method='ffill').fillna(method='bfill')
            
            for symbol in symbols:
                symbol_prices = prices_filled[symbol].tolist()
                all_prices.extend(symbol_prices)

            logger.info(f"Retrieved price history for portfolio '{request.portfolio_name}': {len(symbols)} symbols, {len(prices)} data points")

            return portfolio_pb2.PriceHistory(
                symbols=symbols,
                prices=all_prices
            )
        except Exception as e:
            logger.error(f"GetPriceHistory failed: {e}")
            context.abort(grpc.StatusCode.INTERNAL, "Internal server error")

def serve():
    """Start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    portfolio_pb2_grpc.add_PortfolioServiceServicer_to_server(PortfolioServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.info("gRPC server started on port 50051")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        server.stop(0)

if __name__ == '__main__':
    serve()