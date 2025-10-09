"""
TradingView Alert to IBKR Trading System
Receives webhook alerts from TradingView and executes trades on Interactive Brokers
"""

from flask import Flask, request, jsonify
from ib_insync import IB, Stock, Order, MarketOrder, LimitOrder
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

class IBKRTrader:
    """Handles connection and trading with Interactive Brokers"""
    
    def __init__(self, host='127.0.0.1', port=7497, client_id=1):
        """
        Initialize IBKR connection
        Args:
            host: TWS/IB Gateway host
            port: 7497 for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for Gateway live
            client_id: Unique client ID
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        
    def connect(self):
        """Connect to IBKR TWS or Gateway"""
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            logging.info(f"Connected to IBKR at {self.host}:{self.port}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logging.info("Disconnected from IBKR")
    
    def create_contract(self, symbol: str, sec_type: str = 'STK', 
                       exchange: str = 'SMART', currency: str = 'USD'):
        """
        Create a contract object
        Args:
            symbol: Ticker symbol
            sec_type: Security type (STK, FUT, OPT, etc.)
            exchange: Exchange (SMART for stocks)
            currency: Currency
        """
        if sec_type == 'STK':
            contract = Stock(symbol, exchange, currency)
        else:
            logging.error(f"Security type {sec_type} not implemented")
            return None
        
        # Qualify the contract
        self.ib.qualifyContracts(contract)
        return contract
    
    def place_order(self, symbol: str, action: str, quantity: int, 
                   order_type: str = 'MKT', limit_price: float = None):
        """
        Place an order
        Args:
            symbol: Ticker symbol
            action: 'BUY' or 'SELL'
            quantity: Number of shares
            order_type: 'MKT' or 'LMT'
            limit_price: Limit price (required for LMT orders)
        """
        try:
            if not self.connected:
                if not self.connect():
                    return {'status': 'error', 'message': 'Not connected to IBKR'}
            
            # Create contract
            contract = self.create_contract(symbol)
            if not contract:
                return {'status': 'error', 'message': 'Invalid contract'}
            
            # Create order
            if order_type.upper() == 'MKT':
                order = MarketOrder(action.upper(), quantity)
            elif order_type.upper() == 'LMT':
                if limit_price is None:
                    return {'status': 'error', 'message': 'Limit price required for limit orders'}
                order = LimitOrder(action.upper(), quantity, limit_price)
            else:
                return {'status': 'error', 'message': f'Unknown order type: {order_type}'}
            
            # Place the order
            trade = self.ib.placeOrder(contract, order)
            
            # Wait for order to be submitted
            self.ib.sleep(1)
            
            logging.info(f"Order placed: {action} {quantity} {symbol} @ {order_type}")
            
            return {
                'status': 'success',
                'order_id': trade.order.orderId,
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'order_type': order_type,
                'limit_price': limit_price
            }
            
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_positions(self):
        """Get current positions"""
        try:
            if not self.connected:
                if not self.connect():
                    return []
            
            positions = self.ib.positions()
            return [
                {
                    'symbol': pos.contract.symbol,
                    'position': pos.position,
                    'avg_cost': pos.avgCost
                }
                for pos in positions
            ]
        except Exception as e:
            logging.error(f"Error getting positions: {e}")
            return []

# Initialize trader
trader = IBKRTrader()

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook endpoint to receive TradingView alerts
    
    Expected JSON format:
    {
        "symbol": "AAPL",
        "action": "buy" or "sell",
        "quantity": 100,
        "order_type": "market" or "limit",
        "limit_price": 150.00 (optional, for limit orders),
        "secret": "your_secret_key"
    }
    """
    try:
        # Get JSON data
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        logging.info(f"Received alert: {json.dumps(data)}")
        
        # Verify secret (optional security measure)
        secret = data.get('secret', '')
        expected_secret = 'your_secret_key_here'  # Change this!
        
        if secret != expected_secret:
            logging.warning("Invalid secret key")
            return jsonify({'status': 'error', 'message': 'Invalid secret'}), 401
        
        # Extract order parameters
        symbol = data.get('symbol', '').upper()
        action = data.get('action', '').upper()
        quantity = int(data.get('quantity', 0))
        order_type = data.get('order_type', 'MKT').upper()
        limit_price = data.get('limit_price')
        
        # Validate parameters
        if not symbol:
            return jsonify({'status': 'error', 'message': 'Symbol required'}), 400
        
        if action not in ['BUY', 'SELL']:
            return jsonify({'status': 'error', 'message': 'Action must be BUY or SELL'}), 400
        
        if quantity <= 0:
            return jsonify({'status': 'error', 'message': 'Quantity must be positive'}), 400
        
        # Place the order
        result = trader.place_order(
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price
        )
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/positions', methods=['GET'])
def positions():
    """Get current positions"""
    try:
        pos = trader.get_positions()
        return jsonify({'status': 'success', 'positions': pos}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'connected': trader.connected,
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    """
    SETUP INSTRUCTIONS:
    
    1. Install required packages:
       pip install flask ib_insync
    
    2. Install and run TWS or IB Gateway:
       - Download from IBKR website
       - Enable API connections in settings
       - Set Socket Port (7497 for paper trading)
    
    3. Configure TradingView Alert:
       - Create alert in TradingView
       - Set Webhook URL to: http://your-server:5000/webhook
       - Message format (JSON):
         {
           "symbol": "{{ticker}}",
           "action": "buy",
           "quantity": 100,
           "order_type": "market",
           "secret": "your_secret_key_here"
         }
    
    4. Run this script:
       python tradingview_ibkr.py
    
    5. For production, use a proper WSGI server like gunicorn:
       gunicorn -w 4 -b 0.0.0.0:5000 tradingview_ibkr:app
    """
    
    print("=" * 60)
    print("TradingView to IBKR Trading System")
    print("=" * 60)
    print(f"Starting server at http://0.0.0.0:5000")
    print(f"Webhook endpoint: http://0.0.0.0:5000/webhook")
    print(f"Health check: http://0.0.0.0:5000/health")
    print(f"Positions: http://0.0.0.0:5000/positions")
    print("=" * 60)
    
    # Try to connect to IBKR on startup (non-blocking)
    print("\nAttempting to connect to IBKR...")
    if trader.connect():
        print("✓ Successfully connected to IBKR")
    else:
        print("✗ Could not connect to IBKR")
        print("  Make sure TWS or IB Gateway is running")
        print("  The server will still start and retry connections on each trade")
    
    print("\n" + "=" * 60)
    print("Server is running. Press CTRL+C to stop.")
    print("=" * 60 + "\n")
    
    try:
        # Run Flask app
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        # Disconnect on shutdown
        trader.disconnect()
        print("Server stopped.")