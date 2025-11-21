#!/usr/bin/env python3
"""
Zero-Cost Trading Orchestrator

Manages entire pipeline: data → analysis → decision → execution
All local, all free, all private

Updated to use trading_core.py for deterministic signals and
LLM for regime classification.
"""

import json
import time
import sys
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client import QwenClient
from trading_core import (
    generate_signal,
    compress_ohlcv_for_llm,
    build_regime_prompt,
    aggregate_llm_labels,
    policy_mapper,
)
from ensemble_trading import RegimeEnsembleTrader


class TradingOrchestrator:
    """Main trading pipeline orchestrator"""

    def __init__(self, config_path="./trading_config.json"):
        # Load configuration
        try:
            self.config = json.loads(Path(config_path).read_text())
        except FileNotFoundError:
            print(f"Config file {config_path} not found. Using defaults.")
            self.config = {
                "paper_trading": True,
                "symbol": "BTCUSDT",
                "interval": "1h",
                "server_url": "http://localhost:8000",
                "base_risk_pct": 0.0075,  # 0.75%
                "equity": 10000.0,  # Starting equity
                "num_ensemble_models": 5,
            }

        # Initialize components
        self.llm = QwenClient(base_url=self.config.get("server_url", "http://localhost:8000"))
        self.regime_ensemble = RegimeEnsembleTrader(
            self.llm,
            num_models=self.config.get("num_ensemble_models", 5)
        )

        # Trading state
        self.state = {
            "positions": {},
            "trades_history": [],
            "last_analysis": None,
            "equity": self.config.get("equity", 10000.0),
        }

        # Performance tracking
        self.perf = {
            "avg_latency_ms": 0.0,
            "total_queries": 0,
        }

    def get_market_data(self, symbol="BTCUSDT", interval="1h", limit=250):
        """Fetch market data from Binance public API"""
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            raw = response.json()

            return [
                {
                    "t": c[0],
                    "o": float(c[1]),
                    "h": float(c[2]),
                    "l": float(c[3]),
                    "c": float(c[4]),
                    "v": float(c[5]),
                }
                for c in raw
            ]
        except Exception as e:
            print(f"Error fetching market data: {e}")
            return []

    def pipeline(self, symbol=None, interval=None):
        """
        Main trading pipeline.

        1. Fetch market data
        2. Generate deterministic signal
        3. If signal != flat, get LLM regime classification
        4. Apply policy mapper
        5. Execute trade if order generated

        Returns:
            Decision dict with action and metadata
        """
        start = time.time()

        # Use config defaults if not specified
        symbol = symbol or self.config.get("symbol", "BTCUSDT")
        interval = interval or self.config.get("interval", "1h")
        equity = self.state["equity"]

        try:
            # Step 1: Get market data
            ohlcv = self.get_market_data(symbol, interval)
            if not ohlcv:
                return {"action": "hold", "reason": "no_data"}

            # Step 2: Generate deterministic signal
            signal, meta = generate_signal(ohlcv, symbol, interval)

            if signal == "flat":
                latency = (time.time() - start) * 1000
                self.update_perf(latency)
                return {
                    "action": "hold",
                    "reason": meta.get("reason", "flat"),
                    "metadata": meta,
                }

            # Step 3: Get LLM regime classification
            compressed = compress_ohlcv_for_llm(ohlcv)
            prompt = build_regime_prompt(
                symbol=symbol,
                numeric_regime=meta["numeric_regime"],
                vol_regime=meta["vol_regime"],
                compressed_data=compressed,
            )

            labels_list = self.regime_ensemble.classify_regime(prompt)
            llm_labels = aggregate_llm_labels(labels_list)

            # Step 4: Apply policy mapper
            order = policy_mapper(signal, meta, llm_labels, equity=equity)

            latency = (time.time() - start) * 1000
            self.update_perf(latency)

            if order is None:
                return {
                    "action": "hold",
                    "reason": f"gated_by_llm: regime={llm_labels.regime}, conf={llm_labels.avg_confidence:.1f}",
                    "llm_labels": llm_labels,
                    "metadata": meta,
                }

            # Step 5: Execute trade (paper or live)
            if self.config.get("paper_trading", True):
                self.execute_paper_trade(order)

            return {
                "action": order["action"],
                "order": order,
                "llm_labels": llm_labels,
                "metadata": meta,
            }

        except Exception as e:
            latency = (time.time() - start) * 1000
            self.update_perf(latency)
            return {
                "action": "hold",
                "reason": f"error: {e}",
                "error": str(e),
            }

    def execute_paper_trade(self, order):
        """Execute paper trade (simulation)"""
        trade = {
            "timestamp": datetime.now().isoformat(),
            **order,
        }

        self.state["trades_history"].append(trade)

        # Log to file
        log_file = Path("trades_log.jsonl")
        with log_file.open("a") as f:
            f.write(json.dumps(trade) + "\n")

        print(f"📊 PAPER TRADE: {order['action']} {order['symbol']} @ {order['entry_price']:.2f}")
        print(f"   Qty: {order['qty']:.6f}, Risk: ${order['risk_usd']:.2f}")

    def update_perf(self, latency_ms):
        """Update performance metrics"""
        self.perf["total_queries"] += 1
        self.perf["avg_latency_ms"] = (
            (self.perf["avg_latency_ms"] * (self.perf["total_queries"] - 1) + latency_ms)
            / self.perf["total_queries"]
        )

    def run_continuous(self, sleep_seconds=300):
        """Run continuous trading loop"""
        print("🚀 Starting continuous trading loop...")
        print(f"Symbol: {self.config.get('symbol')}")
        print(f"Interval: {self.config.get('interval')}")
        print(f"Sleep: {sleep_seconds}s between iterations")
        print("-" * 60)

        while True:
            try:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running pipeline...")
                decision = self.pipeline()

                print(f"Decision: {decision['action']}")
                if "reason" in decision:
                    print(f"Reason: {decision['reason']}")

                print(f"Avg Latency: {self.perf['avg_latency_ms']:.0f}ms")
                print(f"Total Queries: {self.perf['total_queries']}")

                time.sleep(sleep_seconds)

            except KeyboardInterrupt:
                print("\n\nStopping trading loop...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(60)  # Wait 1 min on error


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Trading Orchestrator")
    parser.add_argument("--config", default="./trading_config.json", help="Config file path")
    parser.add_argument("--symbol", help="Override symbol")
    parser.add_argument("--interval", help="Override interval")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--sleep", type=int, default=300, help="Sleep seconds between iterations")

    args = parser.parse_args()

    orchestrator = TradingOrchestrator(config_path=args.config)

    if args.once:
        print("Running single iteration...")
        decision = orchestrator.pipeline(symbol=args.symbol, interval=args.interval)
        print("\nDecision:")
        print(json.dumps(decision, indent=2, default=str))

    elif args.continuous:
        orchestrator.run_continuous(sleep_seconds=args.sleep)

    else:
        print("Use --once or --continuous")
        print("Example: python trading_orchestrator.py --once")
        print("Example: python trading_orchestrator.py --continuous --sleep 300")
