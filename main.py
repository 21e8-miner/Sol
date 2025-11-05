"""FastAPI backend for Solana arbitrage bot."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from wallet_manager import wallet_manager
from jupiter_client import jupiter_client
from arbitrage_engine import arbitrage_engine
from trade_executor import trade_executor
from solana.rpc.async_api import AsyncClient
from config import settings


# Background task for monitoring
monitoring_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    # Startup
    print("🚀 Starting Solana Arbitrage Bot...")

    # Load or create wallet
    wallet_manager.load_or_create_wallet()
    print(f"💼 Wallet: {wallet_manager.get_public_key()}")

    # Check balance
    client = AsyncClient(settings.solana_rpc_url)
    balance = await wallet_manager.get_balance(client)
    await client.close()
    print(f"💰 Balance: {balance:.4f} SOL")

    if balance < settings.trade_amount_sol:
        print(f"⚠️  Warning: Balance ({balance:.4f} SOL) is less than trade amount ({settings.trade_amount_sol} SOL)")

    # Start monitoring in background
    global monitoring_task
    monitoring_task = asyncio.create_task(arbitrage_engine.start_monitoring())

    print("✅ Bot started successfully!")

    yield

    # Shutdown
    print("\n🛑 Shutting down...")
    arbitrage_engine.stop_monitoring()

    if monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

    await jupiter_client.close()
    await trade_executor.close()
    print("✅ Shutdown complete")


app = FastAPI(
    title="Solana Arbitrage Bot",
    description="Automated arbitrage bot for Solana DEXes via Jupiter",
    version="1.0.0",
    lifespan=lifespan,
)


# Request/Response Models
class TradeRequest(BaseModel):
    """Request model for manual trade execution."""
    token_a: str
    token_b: str
    amount_sol: Optional[float] = None


class OpportunityResponse(BaseModel):
    """Response model for arbitrage opportunity."""
    token_a: str
    token_b: str
    spread: float
    timestamp: str
    profitable: bool


@app.get("/")
async def root():
    """Root endpoint - returns bot status."""
    client = AsyncClient(settings.solana_rpc_url)
    balance = await wallet_manager.get_balance(client)
    await client.close()

    best_opp = arbitrage_engine.get_best_opportunity()

    return {
        "status": "running",
        "bot": "Solana Arbitrage Bot",
        "wallet": wallet_manager.get_public_key(),
        "balance_sol": round(balance, 4),
        "monitoring": arbitrage_engine.running,
        "opportunities_found": len(arbitrage_engine.opportunities),
        "best_opportunity": {
            "spread": round(best_opp.spread, 2) if best_opp else None,
            "token_pair": f"{best_opp.token_a[:8]}...↔{best_opp.token_b[:8]}..." if best_opp else None,
        } if best_opp else None,
        "config": {
            "min_spread_threshold": settings.min_spread_threshold,
            "trade_amount_sol": settings.trade_amount_sol,
            "scan_interval_seconds": settings.scan_interval_seconds,
            "tokens_monitored": len(settings.tokens_to_monitor),
        },
    }


@app.get("/opportunities", response_model=List[OpportunityResponse])
async def get_opportunities():
    """Get current arbitrage opportunities."""
    opportunities = []

    for opp in arbitrage_engine.opportunities:
        opportunities.append(
            OpportunityResponse(
                token_a=opp.token_a,
                token_b=opp.token_b,
                spread=round(opp.spread, 2),
                timestamp=opp.timestamp.isoformat(),
                profitable=opp.spread >= settings.min_spread_threshold,
            )
        )

    return opportunities


@app.get("/balance")
async def get_balance():
    """Get wallet balance."""
    client = AsyncClient(settings.solana_rpc_url)
    balance = await wallet_manager.get_balance(client)
    await client.close()

    return {
        "wallet": wallet_manager.get_public_key(),
        "balance_sol": round(balance, 4),
        "balance_lamports": int(balance * 1e9),
    }


@app.post("/execute-trade")
async def execute_trade():
    """
    Execute the best arbitrage opportunity automatically.

    This endpoint will:
    1. Find the best current opportunity
    2. Execute the arbitrage trade
    3. Return the results
    """
    # Get best opportunity
    best_opp = arbitrage_engine.get_best_opportunity()

    if not best_opp:
        raise HTTPException(
            status_code=404,
            detail="No arbitrage opportunities found",
        )

    if best_opp.spread < settings.min_spread_threshold:
        raise HTTPException(
            status_code=400,
            detail=f"Best spread ({best_opp.spread:.2f}%) is below threshold ({settings.min_spread_threshold}%)",
        )

    # Check balance
    client = AsyncClient(settings.solana_rpc_url)
    balance = await wallet_manager.get_balance(client)
    await client.close()

    if balance < settings.trade_amount_sol:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance: {balance:.4f} SOL (need {settings.trade_amount_sol} SOL)",
        )

    # Execute the arbitrage
    print(f"\n💹 Executing arbitrage: {best_opp}")
    results = await trade_executor.execute_arbitrage(
        quote_a_to_b=best_opp.quote_a_to_b,
        quote_b_to_a=best_opp.quote_b_to_a,
    )

    if results["success"]:
        return {
            "success": True,
            "message": "Arbitrage executed successfully",
            "spread": round(best_opp.spread, 2),
            "token_a": best_opp.token_a,
            "token_b": best_opp.token_b,
            "transactions": {
                "first_swap": results["first_swap"],
                "second_swap": results["second_swap"],
            },
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Arbitrage execution failed: {results.get('error', 'Unknown error')}",
        )


@app.post("/manual-trade")
async def manual_trade(request: TradeRequest):
    """
    Execute a manual trade for a specific token pair.

    This is useful for testing or executing specific trades.
    """
    amount_sol = request.amount_sol or settings.trade_amount_sol
    amount_lamports = int(amount_sol * 1e9)

    # Check balance
    client = AsyncClient(settings.solana_rpc_url)
    balance = await wallet_manager.get_balance(client)
    await client.close()

    if balance < amount_sol:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance: {balance:.4f} SOL (need {amount_sol} SOL)",
        )

    # Get quotes
    quote_a_to_b = await jupiter_client.get_quote(
        request.token_a, request.token_b, amount_lamports
    )
    if not quote_a_to_b:
        raise HTTPException(
            status_code=500,
            detail="Failed to get quote for A->B swap",
        )

    intermediate_amount = int(quote_a_to_b.get("outAmount", 0))
    quote_b_to_a = await jupiter_client.get_quote(
        request.token_b, request.token_a, intermediate_amount
    )
    if not quote_b_to_a:
        raise HTTPException(
            status_code=500,
            detail="Failed to get quote for B->A swap",
        )

    # Calculate spread
    spread = jupiter_client.calculate_spread(
        quote_a_to_b, quote_b_to_a, amount_lamports
    )

    # Execute
    print(f"\n💹 Executing manual trade: {request.token_a[:8]}...↔{request.token_b[:8]}... (spread: {spread:.2f}%)")
    results = await trade_executor.execute_arbitrage(
        quote_a_to_b=quote_a_to_b,
        quote_b_to_a=quote_b_to_a,
    )

    if results["success"]:
        return {
            "success": True,
            "message": "Manual trade executed successfully",
            "spread": round(spread, 2) if spread else None,
            "transactions": {
                "first_swap": results["first_swap"],
                "second_swap": results["second_swap"],
            },
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Trade execution failed: {results.get('error', 'Unknown error')}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
