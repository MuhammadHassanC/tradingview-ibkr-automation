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
import getpass

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
    
    def __init__(self, host='127.0.0.1', port=7497, client_id=1, username='', account=''):
        """
        Initialize IBKR connection
        Args:
            host: TWS/IB Gateway host
            port: 7497 for TWS paper, 7496 for TWS live, 4002 for Gateway paper, 4001 for Gateway live
            client_id: Unique client ID
            username: IBKR username (optional, for IB Gateway)
            account: Account number (optional)
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self.username = username
        self.account = account
        self.connected = False
        
    def connect(self):
        """Connect to IBKR TWS or Gateway"""
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            
            # Log account information
            accounts = self.ib.managedAccounts()
            if accounts:
                logging.info(f"Available accounts: {', '.join(accounts)}")
                if not self.account:
                    self.account = accounts[0]
                logging.info(f"Using account: {self.account}")
            
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

# Initialize trader (will be configured in main)
trader = None

def get_user_configuration():
    """Interactive setup to get user configuration"""
    print("\n" + "=" * 60)
    print("IBKR CONFIGURATION SETUP")
    print("=" * 60)
    
    # Account Type
    print("\nSelect Account Type:")
    print("1. Paper Trading (recommended for testing)")
    print("2. Live Trading")
    
    while True:
        account_choice = input("\nEnter choice (1 or 2): ").strip()
        if account_choice in ['1', '2']:
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    is_paper = (account_choice == '1')
    
    # Platform Type
    print("\nSelect Platform:")
    print("1. TWS (Trader Workstation)")
    print("2. IB Gateway")
    
    while True:
        platform_choice = input("\nEnter choice (1 or 2): ").strip()
        if platform_choice in ['1', '2']:
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    is_tws = (platform_choice == '1')
    
    # Determine port based on selections
    if is_tws:
        port = 7497 if is_paper else 7496
        platform_name = "TWS"
    else:
        port = 4002 if is_paper else 4001
        platform_name = "IB Gateway"
    
    account_type = "Paper Trading" if is_paper else "Live Trading"
    
    # Host configuration
    print("\nConnection Host:")
    host = input("Enter host (press Enter for localhost/127.0.0.1): ").strip()
    if not host:
        host = '127.0.0.1'
    
    # Client ID
    print("\nClient ID:")
    client_id_input = input("Enter client ID (press Enter for default: 1): ").strip()
    client_id = int(client_id_input) if client_id_input else 1
    
    # Username (optional, mainly for IB Gateway)
    print("\nIBKR Credentials (optional for TWS, required for some IB Gateway setups):")
    username = input("Enter IBKR username (press Enter to skip): ").strip()
    
    # Password (optional)
    password = ""
    if username:
        password = getpass.getpass("Enter IBKR password (hidden): ").strip()
    
    # Account number (optional)
    account = input("\nEnter account number (press Enter to auto-detect): ").strip()
    
    # Secret key for webhook
    print("\nWebhook Security:")
    print("This secret key must match the one in your TradingView alerts")
    secret_key = input("Enter secret key (press Enter for default 'your_secret_key_here'): ").strip()
    if not secret_key:
        secret_key = 'your_secret_key_here'
    
    # Summary
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"Account Type:  {account_type}")
    print(f"Platform:      {platform_name}")
    print(f"Host:          {host}")
    print(f"Port:          {port}")
    print(f"Client ID:     {client_id}")
    print(f"Username:      {username if username else 'Not provided'}")
    print(f"Account:       {account if account else 'Auto-detect'}")
    print(f"Secret Key:    {'*' * len(secret_key)}")
    print("=" * 60)
    
    confirm = input("\nProceed with this configuration? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Configuration cancelled. Exiting...")
        exit(0)
    
    return {
        'host': host,
        'port': port,
        'client_id': client_id,
        'username': username,
        'password': password,
        'account': account,
        'secret_key': secret_key,
        'is_paper': is_paper,
        'platform': platform_name
    }

# Initialize trader (will be configured in main)
trader = None

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
        expected_secret = app.config.get('SECRET_KEY', 'your_secret_key_here')
        
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
    TradingView to IBKR Automated Trading System
    Interactive setup for secure configuration
    """
    
    print("\n" + "=" * 60)
    print("TradingView to IBKR Trading System")
    print("=" * 60)
    print("\nBefore starting, make sure:")
    print("1. TWS or IB Gateway is running")
    print("2. API connections are enabled in TWS/Gateway settings")
    print("3. Socket port is configured correctly")
    print("\n" + "=" * 60)
    
    # Get user configuration
    config = get_user_configuration()
    
    # Store secret key in app config
    app.config['SECRET_KEY'] = config['secret_key']
    
    # Initialize trader with user configuration
    global trader
    trader = IBKRTrader(
        host=config['host'],
        port=config['port'],
        client_id=config['client_id'],
        username=config['username'],
        account=config['account']
    )
    
    print("\n" + "=" * 60)
    print("STARTING SERVER")
    print("=" * 60)
    print(f"Server URL: http://0.0.0.0:5000")
    print(f"Webhook endpoint: http://0.0.0.0:5000/webhook")
    print(f"Health check: http://0.0.0.0:5000/health")
    print(f"Positions: http://0.0.0.0:5000/positions")
    print("=" * 60)
    
    # Try to connect to IBKR on startup
    print(f"\nAttempting to connect to IBKR...")
    print(f"Platform: {config['platform']}")
    print(f"Account Type: {'Paper Trading' if config['is_paper'] else 'Live Trading'}")
    print(f"Connecting to {config['host']}:{config['port']}...\n")
    
    if trader.connect():
        print("✓ Successfully connected to IBKR")
        print(f"✓ Account: {trader.account}")
    else:
        print("✗ Could not connect to IBKR")
        print(f"  Make sure {config['platform']} is running on port {config['port']}")
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
        if trader:
            trader.disconnect()
        print("Server stopped.")