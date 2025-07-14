"""
Production-grade database manager with proper error handling and connection management.
"""
import logging
import sqlite3
import json
import threading
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime

from config import config
from exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Thread-safe SQLite database manager for portfolios and strategies."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path
        self._local = threading.local()
        self._lock = threading.Lock()
        
        logger.info(f"Initialized database manager: {self.db_path}")
        
        # Initialize database schema
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            try:
                self._local.connection = sqlite3.connect(
                    self.db_path,
                    timeout=config.database.timeout,
                    check_same_thread=False
                )
                self._local.connection.row_factory = sqlite3.Row
                logger.debug("Created new database connection")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise DatabaseError(f"Database connection failed: {e}") from e
        
        return self._local.connection
    
    @contextmanager
    def _get_cursor(self):
        """Context manager for database cursor with automatic transaction handling."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise DatabaseError(f"Database operation failed: {e}") from e
        finally:
            cursor.close()
    
    def _initialize_database(self) -> None:
        """Initialize database schema."""
        try:
            with self._get_cursor() as cursor:
                # Portfolios table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS portfolios (
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        holdings TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, name)
                    )
                ''')
                
                # Strategies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS strategies (
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        strategy_type TEXT NOT NULL,
                        parameters TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, name)
                    )
                ''')
                
                # Portfolio history table for tracking changes
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS portfolio_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        portfolio_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        old_holdings TEXT,
                        new_holdings TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_portfolios_user 
                    ON portfolios(user_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_strategies_user 
                    ON strategies(user_id)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_history_user_portfolio 
                    ON portfolio_history(user_id, portfolio_name)
                ''')
                
            logger.info("Database schema initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}") from e
    
    def save_portfolio(self, user_id: str, name: str, holdings: Dict[str, float]) -> None:
        """
        Save or update a portfolio.
        
        Args:
            user_id: User identifier
            name: Portfolio name
            holdings: Dict of symbol -> shares
            
        Raises:
            DatabaseError: If save operation fails
            ValidationError: If inputs are invalid
        """
        self._validate_user_id(user_id)
        self._validate_portfolio_name(name)
        self._validate_holdings(holdings)
        
        try:
            holdings_json = json.dumps(holdings, sort_keys=True)
            
            with self._get_cursor() as cursor:
                # Check if portfolio exists
                cursor.execute(
                    'SELECT holdings FROM portfolios WHERE user_id = ? AND name = ?',
                    (user_id, name)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing portfolio
                    cursor.execute('''
                        UPDATE portfolios 
                        SET holdings = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE user_id = ? AND name = ?
                    ''', (holdings_json, user_id, name))
                    
                    # Log to history
                    cursor.execute('''
                        INSERT INTO portfolio_history 
                        (user_id, portfolio_name, action, old_holdings, new_holdings)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, name, 'UPDATE', existing['holdings'], holdings_json))
                    
                    logger.info(f"Updated portfolio {name} for user {user_id}")
                else:
                    # Create new portfolio
                    cursor.execute('''
                        INSERT INTO portfolios (user_id, name, holdings)
                        VALUES (?, ?, ?)
                    ''', (user_id, name, holdings_json))
                    
                    # Log to history
                    cursor.execute('''
                        INSERT INTO portfolio_history 
                        (user_id, portfolio_name, action, new_holdings)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, name, 'CREATE', holdings_json))
                    
                    logger.info(f"Created portfolio {name} for user {user_id}")
                    
        except json.JSONEncodeError as e:
            logger.error(f"Failed to serialize holdings: {e}")
            raise ValidationError(f"Invalid holdings data: {e}") from e
        except Exception as e:
            logger.error(f"Failed to save portfolio: {e}")
            raise DatabaseError(f"Portfolio save failed: {e}") from e
    
    def load_portfolio(self, user_id: str, name: str) -> Optional[Dict[str, float]]:
        """
        Load a portfolio.
        
        Args:
            user_id: User identifier
            name: Portfolio name
            
        Returns:
            Holdings dict or None if not found
            
        Raises:
            DatabaseError: If load operation fails
        """
        self._validate_user_id(user_id)
        self._validate_portfolio_name(name)
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    'SELECT holdings FROM portfolios WHERE user_id = ? AND name = ?',
                    (user_id, name)
                )
                row = cursor.fetchone()
                
                if row:
                    holdings = json.loads(row['holdings'])
                    logger.debug(f"Loaded portfolio {name} for user {user_id}")
                    return holdings
                else:
                    logger.debug(f"Portfolio {name} not found for user {user_id}")
                    return None
                    
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize holdings: {e}")
            raise DatabaseError(f"Corrupted portfolio data: {e}") from e
        except Exception as e:
            logger.error(f"Failed to load portfolio: {e}")
            raise DatabaseError(f"Portfolio load failed: {e}") from e
    
    def list_portfolios(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all portfolios for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of portfolio info dicts
            
        Raises:
            DatabaseError: If operation fails
        """
        self._validate_user_id(user_id)
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute('''
                    SELECT name, created_at, updated_at 
                    FROM portfolios 
                    WHERE user_id = ? 
                    ORDER BY updated_at DESC
                ''', (user_id,))
                
                portfolios = []
                for row in cursor.fetchall():
                    portfolios.append({
                        'name': row['name'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })
                
                logger.debug(f"Listed {len(portfolios)} portfolios for user {user_id}")
                return portfolios
                
        except Exception as e:
            logger.error(f"Failed to list portfolios: {e}")
            raise DatabaseError(f"Portfolio listing failed: {e}") from e
    
    def delete_portfolio(self, user_id: str, name: str) -> bool:
        """
        Delete a portfolio.
        
        Args:
            user_id: User identifier
            name: Portfolio name
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If operation fails
        """
        self._validate_user_id(user_id)
        self._validate_portfolio_name(name)
        
        try:
            with self._get_cursor() as cursor:
                # Get current holdings for history
                cursor.execute(
                    'SELECT holdings FROM portfolios WHERE user_id = ? AND name = ?',
                    (user_id, name)
                )
                existing = cursor.fetchone()
                
                if not existing:
                    return False
                
                # Delete portfolio
                cursor.execute(
                    'DELETE FROM portfolios WHERE user_id = ? AND name = ?',
                    (user_id, name)
                )
                
                # Log to history
                cursor.execute('''
                    INSERT INTO portfolio_history 
                    (user_id, portfolio_name, action, old_holdings)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, name, 'DELETE', existing['holdings']))
                
                logger.info(f"Deleted portfolio {name} for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete portfolio: {e}")
            raise DatabaseError(f"Portfolio deletion failed: {e}") from e
    
    def save_strategy(self, user_id: str, name: str, strategy_type: str, parameters: Dict[str, Any] = None) -> None:
        """
        Save a strategy configuration.
        
        Args:
            user_id: User identifier
            name: Strategy name
            strategy_type: Type of strategy
            parameters: Strategy parameters
            
        Raises:
            DatabaseError: If save operation fails
        """
        self._validate_user_id(user_id)
        self._validate_strategy_name(name)
        
        try:
            parameters_json = json.dumps(parameters or {}, sort_keys=True)
            
            with self._get_cursor() as cursor:
                cursor.execute('''
                    INSERT OR REPLACE INTO strategies 
                    (user_id, name, strategy_type, parameters, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, name, strategy_type, parameters_json))
                
            logger.info(f"Saved strategy {name} ({strategy_type}) for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to save strategy: {e}")
            raise DatabaseError(f"Strategy save failed: {e}") from e
    
    def load_strategy(self, user_id: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Load a strategy configuration.
        
        Args:
            user_id: User identifier
            name: Strategy name
            
        Returns:
            Strategy config dict or None if not found
        """
        self._validate_user_id(user_id)
        self._validate_strategy_name(name)
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute('''
                    SELECT strategy_type, parameters 
                    FROM strategies 
                    WHERE user_id = ? AND name = ?
                ''', (user_id, name))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'strategy_type': row['strategy_type'],
                        'parameters': json.loads(row['parameters'])
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to load strategy: {e}")
            raise DatabaseError(f"Strategy load failed: {e}") from e
    
    def get_portfolio_history(self, user_id: str, portfolio_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get portfolio change history.
        
        Args:
            user_id: User identifier
            portfolio_name: Portfolio name
            limit: Maximum number of records
            
        Returns:
            List of history records
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute('''
                    SELECT action, old_holdings, new_holdings, timestamp
                    FROM portfolio_history
                    WHERE user_id = ? AND portfolio_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (user_id, portfolio_name, limit))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'action': row['action'],
                        'old_holdings': json.loads(row['old_holdings']) if row['old_holdings'] else None,
                        'new_holdings': json.loads(row['new_holdings']) if row['new_holdings'] else None,
                        'timestamp': row['timestamp']
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Failed to get portfolio history: {e}")
            raise DatabaseError(f"History retrieval failed: {e}") from e
    
    def _validate_user_id(self, user_id: str) -> None:
        """Validate user ID."""
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValidationError("User ID must be a non-empty string")
        if len(user_id) > 100:
            raise ValidationError("User ID too long")
    
    def _validate_portfolio_name(self, name: str) -> None:
        """Validate portfolio name."""
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Portfolio name must be a non-empty string")
        if len(name) > 100:
            raise ValidationError("Portfolio name too long")
    
    def _validate_strategy_name(self, name: str) -> None:
        """Validate strategy name."""
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Strategy name must be a non-empty string")
        if len(name) > 100:
            raise ValidationError("Strategy name too long")
    
    def _validate_holdings(self, holdings: Dict[str, float]) -> None:
        """Validate holdings data."""
        if not isinstance(holdings, dict):
            raise ValidationError("Holdings must be a dictionary")
        
        if not holdings:
            raise ValidationError("Holdings cannot be empty")
        
        for symbol, shares in holdings.items():
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValidationError(f"Invalid symbol: {symbol}")
            if not isinstance(shares, (int, float)) or shares <= 0:
                raise ValidationError(f"Invalid shares for {symbol}: {shares}")
    
    def close(self) -> None:
        """Close database connections."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
            logger.info("Database connection closed")


# Global database manager instance
db_manager = DatabaseManager()