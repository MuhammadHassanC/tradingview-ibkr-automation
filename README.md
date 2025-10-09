# TradingView to IBKR Automated Trading System

A Python-based automated trading system that receives webhook alerts from TradingView and executes trades on Interactive Brokers (IBKR) in real-time.

## Features

- 🔔 Webhook server to receive TradingView alerts
- 📈 Automated order execution on Interactive Brokers
- 🔒 Secret key authentication for security
- 📊 Support for Market and Limit orders
- 📝 Comprehensive logging system
- 🔍 Position tracking endpoint
- ⚡ Real-time trade execution

## Prerequisites

- Python 3.7 or higher
- Interactive Brokers account
- TWS (Trader Workstation) or IB Gateway installed
- TradingView account with alert capabilities

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/tradingview-ibkr-automation.git
cd tradingview-ibkr-automation
```

### 2. Install Required Packages

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
flask==3.0.0
ib_insync==0.9.86
```

### 3. Configure Interactive Brokers

1. **Install TWS or IB Gateway**
   - Download from [Interactive Brokers](https://www.interactivebrokers.com/en/trading/tws.php)

2. **Enable API Access**
   - Open TWS/IB Gateway
   - Go to `File → Global Configuration → API → Settings`
   - Check "Enable ActiveX and Socket Clients"
   - Check "Allow connections from localhost only" (for local testing)
   - Set Socket Port:
     - `7497` for TWS Paper Trading
     - `7496` for TWS Live Trading
     - `4002` for IB Gateway Paper Trading
     - `4001` for IB Gateway Live Trading
   - Uncheck "Read-Only API"

3. **Configure Trusted IPs** (if accessing remotely)
   - Add your server IP to the trusted IP list

## Configuration

### 1. Update Security Settings

Open `tradingview_ibkr.py` and change the secret key:

```python
expected_secret = 'your_secret_key_here'  # Change this to a strong secret!
```

### 2. Update IBKR Connection Settings

Modify the connection parameters if needed:

```python
trader = IBKRTrader(
    host='127.0.0.1',  # TWS/Gateway host
    port=7497,          # Port (7497 for paper trading)
    client_id=1         # Unique client ID
)
```

## Usage

### 1. Start the Server

```bash
python tradingview_ibkr.py
```

The server will start on `http://0.0.0.0:5000`

### 2. Configure TradingView Alert

1. **Create an Alert in TradingView**
   - Open your chart and click the Alert button
   - Set your alert conditions

2. **Configure Webhook**
   - In the Notifications tab, check "Webhook URL"
   - Enter: `http://your-server-ip:5000/webhook`

3. **Set Alert Message (JSON format)**

```json
{
  "symbol": "{{ticker}}",
  "action": "buy",
  "quantity": 100,
  "order_type": "market",
  "secret": "your_secret_key_here"
}
```

**TradingView Variables:**
- `{{ticker}}` - Symbol name
- `{{close}}` - Current close price
- `{{time}}` - Alert trigger time

### 3. Example Alert Messages

**Market Buy Order:**
```json
{
  "symbol": "AAPL",
  "action": "buy",
  "quantity": 50,
  "order_type": "market",
  "secret": "your_secret_key_here"
}
```

**Limit Sell Order:**
```json
{
  "symbol": "TSLA",
  "action": "sell",
  "quantity": 25,
  "order_type": "limit",
  "limit_price": 250.50,
  "secret": "your_secret_key_here"
}
```

**Using TradingView Variables:**
```json
{
  "symbol": "{{ticker}}",
  "action": "buy",
  "quantity": 100,
  "order_type": "limit",
  "limit_price": {{close}},
  "secret": "your_secret_key_here"
}
```

## API Endpoints

### POST /webhook
Receives TradingView alerts and executes trades.

**Request Body:**
```json
{
  "symbol": "AAPL",
  "action": "buy",
  "quantity": 100,
  "order_type": "market",
  "limit_price": 150.00,
  "secret": "your_secret_key_here"
}
```

**Parameters:**
- `symbol` (required): Stock ticker symbol
- `action` (required): "buy" or "sell"
- `quantity` (required): Number of shares (positive integer)
- `order_type` (optional): "market" or "limit" (default: "market")
- `limit_price` (required for limit orders): Price for limit orders
- `secret` (required): Authentication secret key

### GET /positions
Returns current positions from IBKR account.

**Response:**
```json
{
  "status": "success",
  "positions": [
    {
      "symbol": "AAPL",
      "position": 100,
      "avg_cost": 150.25
    }
  ]
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "connected": true,
  "timestamp": "2025-10-09T12:00:00"
}
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 tradingview_ibkr:app
```

### Using systemd (Linux)

Create `/etc/systemd/system/tradingview-ibkr.service`:

```ini
[Unit]
Description=TradingView IBKR Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/tradingview-ibkr-automation
ExecStart=/usr/bin/python3 /path/to/tradingview-ibkr-automation/tradingview_ibkr.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable tradingview-ibkr
sudo systemctl start tradingview-ibkr
sudo systemctl status tradingview-ibkr
```

### Using Docker

**Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tradingview_ibkr.py .

EXPOSE 5000

CMD ["python", "tradingview_ibkr.py"]
```

**Build and run:**
```bash
docker build -t tradingview-ibkr .
docker run -d -p 5000:5000 --name trading-bot tradingview-ibkr
```

### Exposing to Internet (for TradingView webhooks)

If running locally, use ngrok for testing:
```bash
ngrok http 5000
```

For production, use a reverse proxy (nginx) with SSL:
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Logging

All trades and errors are logged to:
- `trading.log` - File log
- Console output

**Log Format:**
```
2025-10-09 12:00:00 - INFO - Order placed: BUY 100 AAPL @ MKT
```

## Security Best Practices

1. **Change the default secret key** immediately
2. Use strong, randomly generated secrets (use `secrets.token_urlsafe(32)`)
3. Use HTTPS for webhook endpoint (SSL/TLS)
4. Restrict IBKR API to localhost when possible
5. Use firewall rules to limit access to webhook endpoint
6. Never commit secrets to version control (use environment variables)
7. Start with paper trading account before going live
8. Implement rate limiting for webhook endpoint
9. Monitor logs regularly for suspicious activity

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to IBKR
```
Failed to connect to IBKR: [Errno 61] Connection refused
```

**Solution:**
- Ensure TWS/IB Gateway is running
- Verify correct port number
- Check API settings are enabled
- Confirm IP address is whitelisted

### Authentication Errors

**Problem:** Invalid secret key warning

**Solution:**
- Verify secret key matches in both code and TradingView alert
- Check for extra spaces or formatting issues in JSON

### Order Rejections

**Problem:** Orders are rejected

**Solution:**
- Check account has sufficient buying power
- Verify market is open for the security
- Confirm order size meets minimum requirements
- Review IBKR account restrictions

## Supported Order Types

- ✅ Market Orders (MKT)
- ✅ Limit Orders (LMT)
- ⏳ Stop Orders (planned)
- ⏳ Stop-Limit Orders (planned)

## Supported Security Types

- ✅ Stocks (STK)
- ⏳ Futures (FUT) - planned
- ⏳ Options (OPT) - planned
- ⏳ Forex (CASH) - planned

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Disclaimer

**⚠️ IMPORTANT: This software is for educational purposes only.**

- Trading stocks and other securities involves risk
- Past performance does not guarantee future results
- Always test with paper trading first
- Use at your own risk - the authors are not responsible for any financial losses
- This is not financial advice
- Ensure compliance with local regulations and IBKR terms of service

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Resources

- [Interactive Brokers API](https://interactivebrokers.github.io/)
- [ib_insync Documentation](https://ib-insync.readthedocs.io/)
- [TradingView Webhooks](https://www.tradingview.com/support/solutions/43000529348-i-want-to-know-more-about-webhooks/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Made with ❤️ for automated trading**