# Self-Hosted Qwen LLM Setup

Complete setup for self-hosting Qwen LLM models and integrating them with Claude Code or any Python environment.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Performance Optimization](#performance-optimization)
- [Architecture](#architecture)

## Overview

This project provides a complete solution for self-hosting Qwen LLM models locally and accessing them via a REST API. It includes:

- **Model Download Scripts**: Easy downloading of Qwen models from Hugging Face
- **API Servers**: Multiple backend options (FastAPI, vLLM)
- **Client Library**: Python client for easy integration
- **Examples**: Comprehensive examples and Jupyter notebooks
- **Claude Code Integration**: Ready-to-use from Claude Code environment

## Features

- ✅ Multiple model sizes supported (0.5B to 72B parameters)
- ✅ CPU and GPU support
- ✅ OpenAI-compatible API endpoints
- ✅ Model quantization support (4-bit, 8-bit)
- ✅ Batch processing capabilities
- ✅ Interactive chat mode
- ✅ Code analysis and debugging helpers
- ✅ Jupyter notebook integration
- ✅ Comprehensive examples

## Requirements

### Software Requirements

- Python >= 3.8 (Python 3.11 recommended)
- pip (Python package manager)
- Git

### Hardware Requirements

The hardware requirements depend on the model size:

| Model Size | GPU VRAM | CPU RAM | Recommended GPU |
|------------|----------|---------|-----------------|
| Qwen2-0.5B | 2 GB     | 8 GB    | RTX 3060 or better |
| Qwen2-1.5B | 4 GB     | 16 GB   | RTX 3060 Ti or better |
| Qwen2-7B   | 16 GB    | 32 GB   | RTX 4090, A100 |
| Qwen2-72B  | 80 GB+   | 128 GB+ | A100 (80GB) or multiple GPUs |

**CPU-Only Option**: You can run smaller models (0.5B, 1.5B) on CPU, but inference will be slower.

### Optional Requirements

- NVIDIA GPU with CUDA support (for faster inference)
- CUDA Toolkit 11.8+ (for GPU acceleration)
- bitsandbytes (for quantization on Linux/CUDA)

## Quick Start

### 1. Install Dependencies

```bash
# Clone or navigate to the project directory
cd qwen_setup

# Install dependencies
pip install -r requirements.txt
```

### 2. Download a Model

```bash
# List available models
python download_model.py --list

# Download Qwen2-1.5B (recommended for testing)
python download_model.py --model qwen2-1.5b --cache-dir ./models
```

### 3. Start the API Server

```bash
# Start FastAPI server (works on CPU and GPU)
python serve_api.py --backend fastapi --model Qwen/Qwen2-1.5B-Instruct

# Or use a local model path
python serve_api.py --backend fastapi --model ./models/Qwen2-1.5B-Instruct
```

The server will start at `http://localhost:8000`.

### 4. Test the Client

In a new terminal:

```bash
# Interactive chat mode
python client.py --interactive

# Simple completion
python client.py --prompt "Explain machine learning in simple terms"

# Check server health
python client.py --health
```

## Detailed Setup

### Installation Options

#### Option 1: Full Installation (GPU Support)

```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt
```

#### Option 2: CPU Only

```bash
# Install PyTorch CPU version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
pip install -r requirements.txt
```

#### Option 3: With vLLM (Requires GPU)

```bash
pip install vllm
pip install -r requirements.txt
```

### Model Download Options

```bash
# Download with default settings
python download_model.py --model qwen2-7b

# Download with 8-bit quantization
python download_model.py --model qwen2-7b --8bit

# Download with 4-bit quantization (smallest size)
python download_model.py --model qwen2-7b --4bit

# Just download, don't load (saves memory)
python download_model.py --model qwen2-7b --download-only

# Custom cache directory
python download_model.py --model qwen2-7b --cache-dir /path/to/models
```

### Server Options

#### FastAPI Server (Recommended for Most Users)

```bash
python serve_api.py --backend fastapi \
  --model Qwen/Qwen2-1.5B-Instruct \
  --host 127.0.0.1 \
  --port 8000
```

**Pros**: Works on CPU and GPU, easy to customize, good for development.

#### vLLM Server (High Performance, GPU Required)

```bash
python serve_api.py --backend vllm \
  --model Qwen/Qwen2-7B-Instruct \
  --host 127.0.0.1 \
  --port 8000
```

**Pros**: Optimized for high throughput, supports batching, production-ready.

## Usage Examples

### Python Script Integration

```python
from client import QwenClient

# Create client
client = QwenClient(base_url="http://localhost:8000")

# Simple completion
response = client.complete("Explain self-hosted LLMs.")
print(response)

# Chat conversation
messages = [
    {"role": "user", "content": "What is Python?"}
]
response = client.chat(messages)
print(response)

# Code analysis
code = "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
analysis = client.analyze_code(code, "Explain this function")
print(analysis)
```

### Claude Code Integration

```python
# From Claude Code or Jupyter notebook
import sys
sys.path.append('/path/to/qwen_setup')

from client import QwenClient

client = QwenClient()
response = client.complete("Explain quantum computing")
print(response)
```

### Interactive Chat

```bash
python client.py --interactive
```

### Batch Processing

```python
from client import QwenClient

client = QwenClient()

prompts = [
    "What is Docker?",
    "What is Kubernetes?",
    "What is a microservice?"
]

for prompt in prompts:
    response = client.complete(prompt, max_tokens=100)
    print(f"Q: {prompt}\nA: {response}\n")
```

### Run Examples

```bash
# Run all example scripts
python examples/example_usage.py

# Open Jupyter notebook
jupyter notebook examples/example_notebook.ipynb
```

## API Reference

### Endpoints

#### Health Check
```
GET /health
```

Returns server health status.

#### List Models
```
GET /v1/models
```

Lists available models.

#### Completions
```
POST /v1/completions

{
  "model": "qwen",
  "prompt": "Your prompt here",
  "max_tokens": 512,
  "temperature": 0.7,
  "top_p": 0.9
}
```

#### Chat Completions
```
POST /v1/chat/completions

{
  "model": "qwen",
  "messages": [
    {"role": "user", "content": "Your message"}
  ],
  "max_tokens": 512,
  "temperature": 0.7
}
```

#### Simple Generate
```
POST /generate

{
  "prompt": "Your prompt",
  "max_tokens": 512,
  "temperature": 0.7
}
```

### Client Methods

```python
# Create client
client = QwenClient(base_url="http://localhost:8000")

# Check health
health = client.health_check()

# List models
models = client.list_models()

# Simple completion
response = client.complete(prompt, max_tokens=512, temperature=0.7)

# Chat
response = client.chat(messages, max_tokens=512, temperature=0.7)

# Code analysis
response = client.analyze_code(code, question)

# Debugging help
response = client.debug_code(code, error)

# Explain concept
response = client.explain_concept(concept, level="beginner")
```

## Troubleshooting

### Common Issues

#### 1. Server Won't Start

**Error**: `Cannot connect to API server`

**Solutions**:
- Make sure you've installed dependencies: `pip install -r requirements.txt`
- Check if port 8000 is available: `lsof -i :8000` (Linux/Mac)
- Try a different port: `python serve_api.py --port 8001`

#### 2. Out of Memory (OOM)

**Error**: `CUDA out of memory` or `Killed`

**Solutions**:
- Use a smaller model (e.g., Qwen2-0.5B or Qwen2-1.5B)
- Enable quantization: `python download_model.py --model qwen2-7b --8bit`
- Use CPU mode (slower): `python serve_api.py --device cpu`

#### 3. Slow Inference

**Solutions**:
- Use GPU if available
- Use vLLM backend for better performance
- Reduce max_tokens parameter
- Use model quantization

#### 4. Model Download Fails

**Error**: Connection timeout or authentication error

**Solutions**:
- Check internet connection
- Login to Hugging Face: `huggingface-cli login`
- Use a VPN if blocked in your region
- Download manually and specify local path

### Environment Detection

This setup was tested on:

```
Python: 3.11.14
OS: Linux 4.4.0
GPU: Not detected (CPU mode available)
```

## Performance Optimization

### GPU Optimization

1. **Use vLLM Backend**
   ```bash
   python serve_api.py --backend vllm --model Qwen/Qwen2-7B-Instruct
   ```

2. **Enable Quantization**
   ```bash
   python download_model.py --model qwen2-7b --8bit
   ```

3. **Adjust GPU Memory**
   - Edit `config.yaml` and set `gpu_memory_fraction: 0.9`

### CPU Optimization

1. **Use Smaller Models**
   - Qwen2-0.5B or Qwen2-1.5B work well on CPU

2. **Reduce Batch Size**
   - Set `batch_size: 1` in config.yaml

3. **Use Lower Precision**
   - Models run in float32 on CPU by default

### Batch Processing

For multiple requests:

```python
# Process multiple prompts efficiently
prompts = ["prompt1", "prompt2", "prompt3"]
responses = [client.complete(p) for p in prompts]
```

## Architecture

### System Overview

```
┌─────────────────┐
│  Claude Code    │
│  or Jupyter     │
└────────┬────────┘
         │
         │ HTTP/REST
         │
┌────────▼────────┐
│  API Server     │
│  (FastAPI/vLLM) │
└────────┬────────┘
         │
         │ Local
         │
┌────────▼────────┐
│  Qwen Model     │
│  (Transformers) │
└─────────────────┘
```

### Components

1. **Model Layer**: Qwen models loaded via Hugging Face Transformers
2. **API Layer**: FastAPI or vLLM providing REST endpoints
3. **Client Layer**: Python client library for easy integration
4. **Integration Layer**: Examples and helpers for Claude Code/Jupyter

### File Structure

```
qwen_setup/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── config.yaml                  # Configuration file
├── download_model.py            # Model download script
├── serve_api.py                 # API server launcher
├── serve_api_fastapi.py         # FastAPI server implementation
├── serve_api_vllm.py            # vLLM server wrapper
├── client.py                    # Client library
├── examples/
│   ├── example_usage.py         # Python examples
│   └── example_notebook.ipynb   # Jupyter notebook
└── models/                      # Model cache (created on first run)
```

## Resources

### Documentation

- [Qwen GitHub Repository](https://github.com/QwenLM/Qwen)
- [Hugging Face Model Cards](https://huggingface.co/Qwen)
- [vLLM Documentation](https://docs.vllm.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Available Qwen Models

| Model | Parameters | Context Length | HuggingFace Path |
|-------|-----------|----------------|------------------|
| Qwen2-0.5B | 0.5B | 32K | Qwen/Qwen2-0.5B-Instruct |
| Qwen2-1.5B | 1.5B | 32K | Qwen/Qwen2-1.5B-Instruct |
| Qwen2-7B | 7B | 32K | Qwen/Qwen2-7B-Instruct |
| Qwen2-72B | 72B | 32K | Qwen/Qwen2-72B-Instruct |

### Hardware Recommendations

For **Development/Testing**:
- Qwen2-1.5B on CPU (8GB RAM)
- Qwen2-1.5B on RTX 3060 (4GB VRAM)

For **Production/Research**:
- Qwen2-7B on RTX 4090 (24GB VRAM)
- Qwen2-7B on A100 (40GB/80GB VRAM)
- Qwen2-72B on multiple A100s or H100

## Security Considerations

- The default server binds to `127.0.0.1` (localhost only)
- For external access, use proper authentication and HTTPS
- Never expose the API publicly without security measures
- Use environment variables for sensitive configuration
- Consider rate limiting for production deployments

## Contributing

Contributions are welcome! Areas for improvement:

- Additional model backends (LMDeploy, text-generation-inference)
- Streaming response support
- WebSocket interface
- Docker containerization
- Kubernetes deployment configs
- Additional examples and use cases

## License

This project is provided as-is for educational and research purposes. Please refer to the Qwen model license for usage terms.

## Acknowledgments

- [QwenLM Team](https://github.com/QwenLM) for the excellent Qwen models
- [vLLM Team](https://github.com/vllm-project/vllm) for high-performance inference
- [Hugging Face](https://huggingface.co/) for model hosting and transformers library

## Next Steps

1. ✅ Install dependencies
2. ✅ Download a model
3. ✅ Start the API server
4. ✅ Run examples
5. 🚀 Integrate with your projects!

For questions or issues, please check the troubleshooting section or refer to the documentation links above.

---

**Happy Self-Hosting! 🚀**
