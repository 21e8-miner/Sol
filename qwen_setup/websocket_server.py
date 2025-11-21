#!/usr/bin/env python3
"""
WebSocket Server for Real-Time Trading UI

Bridges Python trading backend with HTML/JavaScript frontend.
Sends real-time updates: signals, trades, stats, market data.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Set
import time

# Add expert directory to path
sys.path.insert(0, str(Path(__file__).parent / "expert"))

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("Error: websockets not installed. Install with:")
    print("  pip install websockets")
    sys.exit(1)

from trading_orchestrator import TradingOrchestrator


class TradingWebSocketServer:
    """WebSocket server for real-time trading updates"""

    def __init__(self, host="0.0.0.0", port=8765, config_path="./expert/trading_config.json"):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()

        # Initialize trading orchestrator
        self.orchestrator = TradingOrchestrator(config_path=config_path)

        # Stats for UI
        self.stats = {
            "opportunities_found": 0,
            "potential_profit": 0.0,
            "trading_capital": self.orchestrator.state["equity"],
            "total_pnl": 0.0,
            "trades": [],
        }

    async def register(self, websocket: WebSocketServerProtocol):
        """Register new client"""
        self.clients.add(websocket)
        print(f"✅ Client connected: {websocket.remote_address}")

        # Send initial stats
        await self.send_to_client(websocket, {
            "type": "init",
            "stats": self.stats,
            "config": self.orchestrator.config,
        })

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister disconnected client"""
        self.clients.remove(websocket)
        print(f"❌ Client disconnected: {websocket.remote_address}")

    async def send_to_client(self, websocket: WebSocketServerProtocol, message: dict):
        """Send message to a specific client"""
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            print(f"Error sending to client: {e}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if self.clients:
            await asyncio.gather(
                *[self.send_to_client(client, message) for client in self.clients],
                return_exceptions=True
            )

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle individual client connection"""
        await self.register(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(websocket, data)
                except json.JSONDecodeError:
                    await self.send_to_client(websocket, {
                        "type": "error",
                        "message": "Invalid JSON"
                    })
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def handle_message(self, websocket: WebSocketServerProtocol, data: dict):
        """Handle incoming message from client"""
        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send_to_client(websocket, {"type": "pong"})

        elif msg_type == "get_stats":
            await self.send_to_client(websocket, {
                "type": "stats",
                "stats": self.stats
            })

        elif msg_type == "run_analysis":
            # Run trading pipeline once
            await self.run_analysis_once()

        elif msg_type == "start_autonomous":
            # Start continuous trading
            asyncio.create_task(self.run_continuous())

        else:
            await self.send_to_client(websocket, {
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            })

    async def run_analysis_once(self):
        """Run trading analysis once and broadcast results"""
        await self.broadcast({
            "type": "log",
            "level": "info",
            "message": "Running trading analysis..."
        })

        try:
            decision = self.orchestrator.pipeline()

            # Update stats
            if decision["action"] != "hold":
                self.stats["opportunities_found"] += 1

                if "order" in decision:
                    order = decision["order"]
                    potential_profit = order["qty"] * (order["take_profit"] - order["entry_price"])
                    self.stats["potential_profit"] += potential_profit

                    # Add to trades list
                    self.stats["trades"].append({
                        "timestamp": datetime.now().isoformat(),
                        "symbol": order["symbol"],
                        "action": order["action"],
                        "price": order["entry_price"],
                        "qty": order["qty"],
                        "potential_profit": potential_profit,
                    })

            # Broadcast decision
            await self.broadcast({
                "type": "decision",
                "decision": decision,
                "stats": self.stats,
            })

            # Broadcast log
            level = "success" if decision["action"] != "hold" else "info"
            message = f"Decision: {decision['action']}"
            if "reason" in decision:
                message += f" - {decision['reason']}"

            await self.broadcast({
                "type": "log",
                "level": level,
                "message": message
            })

        except Exception as e:
            await self.broadcast({
                "type": "log",
                "level": "error",
                "message": f"Analysis error: {str(e)}"
            })

    async def run_continuous(self):
        """Run continuous trading analysis"""
        await self.broadcast({
            "type": "log",
            "level": "success",
            "message": "🚀 Autonomous mode activated"
        })

        sleep_seconds = 300  # 5 minutes

        while True:
            try:
                await self.run_analysis_once()
                await asyncio.sleep(sleep_seconds)

            except Exception as e:
                await self.broadcast({
                    "type": "log",
                    "level": "error",
                    "message": f"Error in continuous loop: {str(e)}"
                })
                await asyncio.sleep(60)  # Wait 1 min on error

    async def market_data_streamer(self):
        """Stream simulated market data for UI charts"""
        import random

        price = 45000.0

        while True:
            # Simulate price updates
            price += random.uniform(-50, 50)

            await self.broadcast({
                "type": "market_data",
                "symbol": "BTCUSDT",
                "price": price,
                "timestamp": time.time() * 1000,  # milliseconds
            })

            await asyncio.sleep(1)  # 1 update per second

    async def start(self):
        """Start WebSocket server"""
        print("=" * 60)
        print("🌐 Trading WebSocket Server")
        print("=" * 60)
        print(f"Host: {self.host}")
        print(f"Port: {self.port}")
        print(f"WebSocket URL: ws://{self.host}:{self.port}")
        print("=" * 60)
        print()

        # Start market data streamer
        asyncio.create_task(self.market_data_streamer())

        async with websockets.serve(self.handle_client, self.host, self.port):
            print("✅ WebSocket server started")
            print("Waiting for connections...")
            print("Press Ctrl+C to stop")
            print()

            await asyncio.Future()  # Run forever


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Trading WebSocket Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument("--config", default="./expert/trading_config.json", help="Config file")

    args = parser.parse_args()

    server = TradingWebSocketServer(
        host=args.host,
        port=args.port,
        config_path=args.config
    )

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n\nShutting down...")


if __name__ == "__main__":
    main()
