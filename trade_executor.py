"""Trade execution module for Solana arbitrage bot."""
import base64
from typing import Optional, Dict, Any
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.transaction import VersionedTransaction
from wallet_manager import wallet_manager
from jupiter_client import jupiter_client
from config import settings


class TradeExecutor:
    """Executes trades on Solana via Jupiter."""

    def __init__(self):
        """Initialize trade executor."""
        self.client = AsyncClient(settings.solana_rpc_url)

    async def execute_swap(
        self,
        quote: Dict[str, Any],
    ) -> Optional[str]:
        """
        Execute a swap based on a Jupiter quote.

        Args:
            quote: Quote from Jupiter API

        Returns:
            Transaction signature if successful, None otherwise
        """
        try:
            # Get user public key
            user_pubkey = wallet_manager.get_public_key()

            # Get swap transaction from Jupiter
            swap_response = await jupiter_client.get_swap_transaction(
                quote=quote,
                user_public_key=user_pubkey,
            )

            if not swap_response:
                print("❌ Failed to get swap transaction")
                return None

            # Get the serialized transaction
            swap_transaction = swap_response.get("swapTransaction")
            if not swap_transaction:
                print("❌ No swap transaction in response")
                return None

            # Decode the transaction
            transaction_bytes = base64.b64decode(swap_transaction)

            # Deserialize and sign the transaction
            try:
                # Try as VersionedTransaction
                versioned_tx = VersionedTransaction.from_bytes(transaction_bytes)

                # Sign the transaction
                signature = wallet_manager.keypair.sign_message(
                    bytes(versioned_tx.message)
                )

                # Send the transaction
                response = await self.client.send_raw_transaction(
                    transaction_bytes,
                    opts={"skip_preflight": False, "preflight_commitment": "confirmed"},
                )

                tx_sig = response.value
                print(f"✅ Transaction sent: {tx_sig}")

                return str(tx_sig)

            except Exception as e:
                print(f"❌ Error processing transaction: {e}")
                return None

        except Exception as e:
            print(f"❌ Error executing swap: {e}")
            return None

    async def execute_arbitrage(
        self,
        quote_a_to_b: Dict[str, Any],
        quote_b_to_a: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a full arbitrage cycle (A -> B -> A).

        Args:
            quote_a_to_b: Quote for first swap
            quote_b_to_a: Quote for second swap

        Returns:
            Dictionary with execution results
        """
        results = {
            "success": False,
            "first_swap": None,
            "second_swap": None,
            "error": None,
        }

        try:
            # Execute first swap (A -> B)
            print("🔄 Executing first swap (A -> B)...")
            first_sig = await self.execute_swap(quote_a_to_b)

            if not first_sig:
                results["error"] = "First swap failed"
                return results

            results["first_swap"] = first_sig

            # Wait a bit for the first transaction to settle
            import asyncio
            await asyncio.sleep(2)

            # Execute second swap (B -> A)
            print("🔄 Executing second swap (B -> A)...")
            second_sig = await self.execute_swap(quote_b_to_a)

            if not second_sig:
                results["error"] = "Second swap failed (first swap succeeded)"
                return results

            results["second_swap"] = second_sig
            results["success"] = True

            print("✅ Arbitrage executed successfully!")
            return results

        except Exception as e:
            results["error"] = str(e)
            print(f"❌ Error during arbitrage execution: {e}")
            return results

    async def close(self):
        """Close the RPC client."""
        await self.client.close()


# Global trade executor instance
trade_executor = TradeExecutor()
