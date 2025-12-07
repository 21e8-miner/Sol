#!/usr/bin/env python3
"""
Test client for WebSocket trading server
Simulates what the HTML UI does
"""

import asyncio
import websockets
import json

async def test_client():
    uri = "ws://localhost:8765"

    print("🔌 Connecting to WebSocket server...")

    async with websockets.connect(uri) as websocket:
        print("✅ Connected!")

        # Wait for init message
        init_msg = await websocket.recv()
        data = json.loads(init_msg)
        print(f"\n📊 Initial Stats:")
        print(json.dumps(data, indent=2))

        # Request a single analysis
        print("\n🔍 Requesting trading analysis...")
        await websocket.send(json.dumps({"type": "run_analysis"}))

        # Listen for responses for 30 seconds
        print("\n📡 Listening for updates (30s)...\n")
        try:
            async with asyncio.timeout(30):
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    if data['type'] == 'log':
                        level = data['level'].upper()
                        msg = data['message']
                        print(f"[{level}] {msg}")

                    elif data['type'] == 'decision':
                        print(f"\n🎯 DECISION: {data['decision']['action']}")
                        if 'reason' in data['decision']:
                            print(f"   Reason: {data['decision']['reason']}")
                        print(f"   Stats: {data['stats']}")

                    elif data['type'] == 'market_data':
                        # Just show first few
                        pass

        except asyncio.TimeoutError:
            print("\n⏱️  Test complete!")

if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Trading Client Test")
    print("=" * 60)
    asyncio.run(test_client())
