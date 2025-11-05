"""Jupiter API client for fetching price quotes."""
import httpx
from typing import Optional, Dict, Any
from config import settings


class JupiterClient:
    """Client for interacting with Jupiter Aggregator API."""

    def __init__(self):
        """Initialize Jupiter client."""
        self.base_url = settings.jupiter_api_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a quote from Jupiter API.

        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount in smallest unit (lamports for SOL)
            slippage_bps: Slippage tolerance in basis points (50 = 0.5%)

        Returns:
            Quote data or None if error
        """
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": slippage_bps,
            }

            response = await self.client.get(f"{self.base_url}/quote", params=params)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error fetching quote: {e}")
            return None

    async def get_swap_transaction(
        self,
        quote: Dict[str, Any],
        user_public_key: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get swap transaction from Jupiter API.

        Args:
            quote: Quote object from get_quote
            user_public_key: User's wallet public key

        Returns:
            Swap transaction data or None if error
        """
        try:
            payload = {
                "quoteResponse": quote,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True,
            }

            response = await self.client.post(
                f"{self.base_url}/swap",
                json=payload,
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error fetching swap transaction: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def calculate_spread(
        self,
        quote_a_to_b: Optional[Dict[str, Any]],
        quote_b_to_a: Optional[Dict[str, Any]],
        initial_amount: int,
    ) -> Optional[float]:
        """
        Calculate arbitrage spread percentage.

        Args:
            quote_a_to_b: Quote for A -> B swap
            quote_b_to_a: Quote for B -> A swap
            initial_amount: Initial amount in smallest unit

        Returns:
            Spread percentage or None if quotes invalid
        """
        if not quote_a_to_b or not quote_b_to_a:
            return None

        try:
            # Get output amount from first swap (A -> B)
            intermediate_amount = int(quote_a_to_b.get("outAmount", 0))

            # Get output amount from second swap (B -> A)
            final_amount = int(quote_b_to_a.get("outAmount", 0))

            if initial_amount == 0:
                return None

            # Calculate spread percentage
            spread = ((final_amount - initial_amount) / initial_amount) * 100

            return spread
        except Exception as e:
            print(f"Error calculating spread: {e}")
            return None


# Global Jupiter client instance
jupiter_client = JupiterClient()
