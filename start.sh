#!/bin/bash

# Solana Arbitrage Bot Startup Script

echo "🚀 Starting Solana Arbitrage Bot..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists, if not copy from example
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📄 Creating .env file from .env.example..."
        cp .env.example .env
        echo "⚠️  Please edit .env file with your configuration!"
    fi
fi

# Start the bot
echo "✅ Starting bot..."
python main.py
