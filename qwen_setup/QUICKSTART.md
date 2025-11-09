# Quick Start Guide

Get your self-hosted Qwen LLM running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- 8GB RAM minimum (16GB recommended)
- Internet connection for downloading models

## Step 1: Install Dependencies

### Option A: Automated Setup (Recommended)

```bash
cd qwen_setup
bash setup.sh
```

### Option B: Manual Setup

```bash
cd qwen_setup
pip install -r requirements.txt
```

## Step 2: Download a Model

Choose a model based on your hardware:

### For CPU or Limited GPU (4GB VRAM):
```bash
python download_model.py --model qwen2-1.5b
```

### For GPU with 16GB+ VRAM:
```bash
python download_model.py --model qwen2-7b
```

**This will take a few minutes depending on your internet speed.**

## Step 3: Start the Server

```bash
python serve_api.py --backend fastapi --model Qwen/Qwen2-1.5B-Instruct
```

Wait for the message: "Uvicorn running on http://127.0.0.1:8000"

## Step 4: Test It!

Open a **new terminal** and run:

### Interactive Chat
```bash
python client.py --interactive
```

Type your questions and press Enter. Type `/quit` to exit.

### Single Query
```bash
python client.py --prompt "Explain machine learning in simple terms"
```

### Check Health
```bash
python client.py --health
```

## Step 5: Use in Your Code

Create a Python script or use from Claude Code:

```python
from client import QwenClient

client = QwenClient(base_url="http://localhost:8000")

# Simple completion
response = client.complete("What is Python?")
print(response)

# Chat
messages = [
    {"role": "user", "content": "Tell me about AI"}
]
response = client.chat(messages)
print(response)
```

## Common Commands

```bash
# List available models
python download_model.py --list

# Start server on different port
python serve_api.py --port 8001

# Interactive chat
python client.py -i

# Run examples
python examples/example_usage.py

# Open Jupyter notebook
jupyter notebook examples/example_notebook.ipynb
```

## Troubleshooting

### Server won't start?
- Check if port 8000 is available
- Make sure dependencies are installed: `pip install -r requirements.txt`

### Out of memory?
- Use a smaller model: `qwen2-0.5b` or `qwen2-1.5b`
- Enable quantization: `python download_model.py --model qwen2-7b --8bit`

### Slow responses?
- Normal on CPU (30-60 seconds for first response)
- Use GPU if available for faster inference
- Reduce max_tokens: `client.complete(prompt, max_tokens=100)`

## What's Next?

1. Check out `examples/example_usage.py` for more patterns
2. Read the full `README.md` for detailed documentation
3. Try the Jupyter notebook: `examples/example_notebook.ipynb`
4. Integrate with your Claude Code projects!

## Architecture

```
Your Code → HTTP API → Qwen Model → Response
```

Simple as that!

---

For detailed information, see [README.md](README.md)
