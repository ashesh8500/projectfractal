from ib_insync import IB, Stock, Order
from typing import List, Dict
import pandas as pd

class IBConnector:
    """Connects to Interactive Brokers for live data and orders."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 7497, client_id: int = 1):
        self.ib = IB()
        self.ib.connect(host, port, client_id)

    def get_live_prices(self, symbols: List[str]) -> Dict[str, float]:
        contracts = [Stock(symbol, 'SMART', 'USD') for symbol in symbols]
        self.ib.qualifyContracts(*contracts)
        ticks = self.ib.reqMktData(*contracts)
        prices = {}
        for contract, tick in zip(contracts, ticks):
            self.ib.sleep(1)  # Wait for data
            prices[contract.symbol] = tick.last if tick.last else tick.close
        return prices

    def place_orders(self, orders: pd.DataFrame):
        for _, row in orders.iterrows():
            contract = Stock(row['asset'], 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            order = Order()
            order.action = 'BUY' if row['order_size'] > 0 else 'SELL'
            order.totalQuantity = abs(row['order_size'])
            order.orderType = 'MKT'
            trade = self.ib.placeOrder(contract, order)
            print(f"Placed order for {row['asset']}: {trade}")

    def disconnect(self):
        self.ib.disconnect()
