"""Arbitrage detection and execution engine."""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from jupiter_client import jupiter_client
from config import settings


class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""

    def __init__(
        self,
        token_a: str,
        token_b: str,
        spread: float,
        quote_a_to_b: Dict,
        quote_b_to_a: Dict,
        timestamp: datetime,
    ):
        self.token_a = token_a
        self.token_b = token_b
        self.spread = spread
        self.quote_a_to_b = quote_a_to_b
        self.quote_b_to_a = quote_b_to_a
        self.timestamp = timestamp

    def __repr__(self):
        return f"ArbitrageOpportunity({self.token_a[:8]}...↔{self.token_b[:8]}..., spread={self.spread:.2f}%)"


class ArbitrageEngine:
    """Engine for detecting and executing arbitrage opportunities."""

    def __init__(self):
        """Initialize arbitrage engine."""
        self.sol_mint = "So11111111111111111111111111111111111111112"
        self.running = False
        self.opportunities: List[ArbitrageOpportunity] = []

    async def scan_for_opportunities(self) -> List[ArbitrageOpportunity]:
        """
        Scan for arbitrage opportunities.

        Returns:
            List of arbitrage opportunities found
        """
        opportunities = []

        # Convert trade amount to lamports
        amount_lamports = int(settings.trade_amount_sol * 1e9)

        # Scan each token pair
        for token in settings.tokens_to_monitor:
            if token == self.sol_mint:
                continue  # Skip SOL to SOL

            # Try SOL -> Token -> SOL arbitrage
            opportunity = await self._check_arbitrage_pair(
                self.sol_mint, token, amount_lamports
            )

            if opportunity and opportunity.spread >= settings.min_spread_threshold:
                opportunities.append(opportunity)
                print(f"🎯 Found opportunity: {opportunity}")

        return opportunities

    async def _check_arbitrage_pair(
        self, token_a: str, token_b: str, amount: int
    ) -> Optional[ArbitrageOpportunity]:
        """
        Check for arbitrage opportunity between two tokens.

        Args:
            token_a: First token mint address
            token_b: Second token mint address
            amount: Amount to trade in smallest unit

        Returns:
            ArbitrageOpportunity if found, None otherwise
        """
        try:
            # Get quotes for both directions
            quote_a_to_b = await jupiter_client.get_quote(token_a, token_b, amount)
            if not quote_a_to_b:
                return None

            # Get intermediate amount
            intermediate_amount = int(quote_a_to_b.get("outAmount", 0))
            if intermediate_amount == 0:
                return None

            # Get quote for reverse swap
            quote_b_to_a = await jupiter_client.get_quote(
                token_b, token_a, intermediate_amount
            )
            if not quote_b_to_a:
                return None

            # Calculate spread
            spread = jupiter_client.calculate_spread(
                quote_a_to_b, quote_b_to_a, amount
            )

            if spread is not None and spread > 0:
                return ArbitrageOpportunity(
                    token_a=token_a,
                    token_b=token_b,
                    spread=spread,
                    quote_a_to_b=quote_a_to_b,
                    quote_b_to_a=quote_b_to_a,
                    timestamp=datetime.now(),
                )

            return None

        except Exception as e:
            print(f"Error checking arbitrage pair: {e}")
            return None

    async def start_monitoring(self):
        """Start continuous monitoring for arbitrage opportunities."""
        self.running = True
        print(f"🔄 Starting arbitrage monitoring (interval: {settings.scan_interval_seconds}s)")
        print(f"💰 Trade amount: {settings.trade_amount_sol} SOL")
        print(f"📊 Min spread threshold: {settings.min_spread_threshold}%")
        print(f"🪙 Monitoring {len(settings.tokens_to_monitor)} tokens")

        while self.running:
            try:
                opportunities = await self.scan_for_opportunities()
                self.opportunities = opportunities

                if opportunities:
                    print(f"\n✅ Found {len(opportunities)} opportunities:")
                    for opp in opportunities:
                        print(f"  {opp}")
                else:
                    print(".", end="", flush=True)

            except Exception as e:
                print(f"\n❌ Error during monitoring: {e}")

            await asyncio.sleep(settings.scan_interval_seconds)

    def stop_monitoring(self):
        """Stop monitoring for arbitrage opportunities."""
        self.running = False
        print("\n🛑 Stopping arbitrage monitoring")

    def get_best_opportunity(self) -> Optional[ArbitrageOpportunity]:
        """Get the best arbitrage opportunity by spread."""
        if not self.opportunities:
            return None

        return max(self.opportunities, key=lambda x: x.spread)


# Global arbitrage engine instance
arbitrage_engine = ArbitrageEngine()
