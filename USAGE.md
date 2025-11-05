# Solana Arbitrage Bot - Usage Guide

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd Sol

# Run the startup script (creates venv and installs dependencies)
./start.sh
```

Or manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

### 2. Configuration

Copy `.env.example` to `.env` and adjust settings:

```bash
cp .env.example .env
```

Key configuration options:
- `SOLANA_RPC_URL`: Solana RPC endpoint (default: mainnet-beta)
- `MIN_SPREAD_THRESHOLD`: Minimum spread % to consider profitable (default: 0.5%)
- `TRADE_AMOUNT_SOL`: Amount to trade in SOL (default: 0.1)
- `SCAN_INTERVAL_SECONDS`: How often to scan for opportunities (default: 5s)

### 3. Wallet Setup

On first run, the bot will automatically generate a new wallet at `wallet.json`.

**IMPORTANT:** Fund this wallet with SOL before trading!

```bash
# The bot will display the wallet address on startup
# Send SOL to this address using any Solana wallet
```

## API Endpoints

The bot runs a FastAPI server on `http://localhost:8000`

### GET `/`
Returns bot status, balance, and current opportunities.

```bash
curl http://localhost:8000/
```

### GET `/opportunities`
Lists all current arbitrage opportunities.

```bash
curl http://localhost:8000/opportunities
```

### GET `/balance`
Check wallet balance.

```bash
curl http://localhost:8000/balance
```

### POST `/execute-trade`
Automatically execute the best arbitrage opportunity.

```bash
curl -X POST http://localhost:8000/execute-trade
```

### POST `/manual-trade`
Execute arbitrage for a specific token pair.

```bash
curl -X POST http://localhost:8000/manual-trade \
  -H "Content-Type: application/json" \
  -d '{
    "token_a": "So11111111111111111111111111111111111111112",
    "token_b": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "amount_sol": 0.1
  }'
```

## How It Works

1. **Scanning**: The bot continuously scans Jupiter Aggregator for price quotes
2. **Detection**: Calculates potential profit from A→B→A arbitrage cycles
3. **Filtering**: Only considers opportunities above the minimum spread threshold
4. **Execution**: Executes profitable trades automatically (or via API)

## Deployment

### Render.com

1. Push code to GitHub
2. Connect repository to Render
3. Render will detect `render.yaml` and deploy automatically
4. Add your wallet private key as an environment variable (or let bot generate one)

### Docker

```bash
# Build
docker build -t solana-arbitrage-bot .

# Run
docker run -p 8000:8000 -v $(pwd)/wallet.json:/app/wallet.json solana-arbitrage-bot
```

## Safety Notes

- Start with small trade amounts (`TRADE_AMOUNT_SOL=0.01`)
- Monitor the bot closely during initial runs
- Keep sufficient SOL for transaction fees
- Arbitrage opportunities are competitive - high spreads close quickly
- Consider using a custom RPC endpoint for better performance

## Troubleshooting

### Bot finds no opportunities
- Lower `MIN_SPREAD_THRESHOLD` (try 0.1%)
- Increase `TRADE_AMOUNT_SOL` for better liquidity
- Use a faster RPC endpoint
- Add more tokens to monitor in `config.py`

### Transactions failing
- Check wallet balance (need SOL for fees)
- Verify RPC endpoint is responsive
- Reduce trade amount if liquidity is low

### Rate limiting
- Use a paid RPC endpoint (Helius, QuickNode, etc.)
- Increase `SCAN_INTERVAL_SECONDS`

## Token Addresses

Common Solana tokens:
- SOL: `So11111111111111111111111111111111111111112`
- USDC: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- USDT: `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB`
- mSOL: `mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So`

## License

MIT License - Use at your own risk. Trading cryptocurrencies carries significant risk.
