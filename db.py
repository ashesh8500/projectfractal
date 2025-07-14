import sqlite3
import json
from typing import Dict, List

class DBManager:
    """SQLite DB for saving portfolios and strategies."""
    
    def __init__(self, db_path: str = 'portfolio.db'):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS portfolios
                          (user_id TEXT, name TEXT, data TEXT, PRIMARY KEY (user_id, name))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS strategies
                          (user_id TEXT, name TEXT, code TEXT, PRIMARY KEY (user_id, name))''')
        self.conn.commit()

    def save_portfolio(self, user_id: str, name: str, holdings: Dict[str, float]):
        data_json = json.dumps(holdings)
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO portfolios (user_id, name, data) VALUES (?, ?, ?)',
                       (user_id, name, data_json))
        self.conn.commit()

    def load_portfolios(self, user_id: str) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT name FROM portfolios WHERE user_id = ?', (user_id,))
        return [row[0] for row in cursor.fetchall()]

    def load_portfolio(self, user_id: str, name: str) -> Dict[str, float]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT data FROM portfolios WHERE user_id = ? AND name = ?', (user_id, name))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}

    def save_strategy(self, user_id: str, name: str, code: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO strategies (user_id, name, code) VALUES (?, ?, ?)',
                       (user_id, name, code))
        self.conn.commit()

    def load_strategies(self, user_id: str) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT name FROM strategies WHERE user_id = ?', (user_id,))
        return [row[0] for row in cursor.fetchall()]

    def load_strategy_code(self, user_id: str, name: str) -> str:
        cursor = self.conn.cursor()
        cursor.execute('SELECT code FROM strategies WHERE user_id = ? AND name = ?', (user_id, name))
        row = cursor.fetchone()
        if row:
            return row[0]
        return ""
