"""Configuration settings for the Solana arbitrage bot."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Solana RPC Configuration
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"

    # Jupiter API Configuration
    jupiter_api_url: str = "https://quote-api.jup.ag/v6"

    # Wallet Configuration
    wallet_path: str = "wallet.json"

    # Trading Configuration
    min_spread_threshold: float = 0.5  # Minimum spread percentage for trading
    trade_amount_sol: float = 0.1  # Amount to trade in SOL

    # Arbitrage Configuration
    scan_interval_seconds: int = 5  # How often to scan for arbitrage opportunities

    # Token pairs to monitor (SOL to other tokens)
    tokens_to_monitor: list[str] = [
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        "So11111111111111111111111111111111111111112",   # SOL (wrapped)
        "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
    ]

    class Config:
        env_file = ".env"


settings = Settings()
