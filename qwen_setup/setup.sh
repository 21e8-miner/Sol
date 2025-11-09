#!/bin/bash

# Qwen Self-Hosting Quick Setup Script

set -e  # Exit on error

echo "========================================"
echo "Qwen Self-Hosting Setup"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    echo "Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python $PYTHON_VERSION"

# Check if version is >= 3.8
if (( $(echo "$PYTHON_VERSION < 3.8" | bc -l) )); then
    echo "Error: Python version must be 3.8 or higher."
    echo "Found: $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python version OK"
echo ""

# Detect GPU
echo "Checking for NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected:"
    nvidia-smi --query-gpu=name --format=csv,noheader
    GPU_AVAILABLE=1
else
    echo "⚠ No NVIDIA GPU detected. Will use CPU mode (slower)."
    GPU_AVAILABLE=0
fi
echo ""

# Ask user for installation type
echo "Select installation type:"
echo "1) Full installation with GPU support (recommended if you have a GPU)"
echo "2) CPU-only installation"
echo "3) Custom (I'll install PyTorch myself)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        if [ $GPU_AVAILABLE -eq 0 ]; then
            echo "⚠ Warning: GPU not detected but GPU installation selected."
            read -p "Continue anyway? [y/N]: " confirm
            if [[ ! $confirm =~ ^[Yy]$ ]]; then
                echo "Installation cancelled."
                exit 0
            fi
        fi
        echo "Installing with GPU support..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        ;;
    2)
        echo "Installing CPU-only version..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        ;;
    3)
        echo "Skipping PyTorch installation."
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Installing other dependencies..."
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Download a model:"
echo "   python download_model.py --model qwen2-1.5b"
echo ""
echo "2. Start the API server:"
echo "   python serve_api.py --backend fastapi --model Qwen/Qwen2-1.5B-Instruct"
echo ""
echo "3. Test the client:"
echo "   python client.py --interactive"
echo ""
echo "For more information, see README.md"
echo ""
