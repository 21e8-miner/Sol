"""Wallet management for the Solana arbitrage bot."""
import json
import os
from pathlib import Path
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from config import settings


class WalletManager:
    """Manages Solana wallet operations."""

    def __init__(self, wallet_path: str = None):
        """Initialize wallet manager."""
        self.wallet_path = wallet_path or settings.wallet_path
        self.keypair: Keypair = None
        self.pubkey: Pubkey = None

    def load_or_create_wallet(self) -> Keypair:
        """Load existing wallet or create a new one."""
        wallet_file = Path(self.wallet_path)

        if wallet_file.exists():
            print(f"Loading existing wallet from {self.wallet_path}")
            with open(wallet_file, "r") as f:
                data = json.load(f)
                # Keypair is stored as array of bytes
                secret_key = bytes(data)
                self.keypair = Keypair.from_bytes(secret_key)
        else:
            print(f"Creating new wallet at {self.wallet_path}")
            self.keypair = Keypair()

            # Save wallet to file
            with open(wallet_file, "w") as f:
                # Save as array of bytes
                json.dump(list(bytes(self.keypair)), f)

            print(f"⚠️  New wallet created!")
            print(f"Public key: {self.keypair.pubkey()}")
            print(f"⚠️  Please fund this wallet with SOL before trading!")

        self.pubkey = self.keypair.pubkey()
        return self.keypair

    async def get_balance(self, client: AsyncClient) -> float:
        """Get wallet balance in SOL."""
        try:
            response = await client.get_balance(self.pubkey)
            # Convert lamports to SOL (1 SOL = 1e9 lamports)
            balance_sol = response.value / 1e9
            return balance_sol
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return 0.0

    def get_public_key(self) -> str:
        """Get wallet public key as string."""
        return str(self.pubkey)


# Global wallet instance
wallet_manager = WalletManager()
