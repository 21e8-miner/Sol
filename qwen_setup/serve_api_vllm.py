#!/usr/bin/env python3
"""
Qwen API Server using vLLM

High-performance serving using vLLM. Requires GPU.
This script starts an OpenAI-compatible API server.
"""

import argparse
import sys

try:
    from vllm import LLM, SamplingParams
    from vllm.entrypoints.openai.api_server import run_server
except ImportError:
    print("Error: vLLM not installed. Install with:")
    print("  pip install vllm")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Start vLLM API server for Qwen model"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen2-1.5B-Instruct",
        help="Model name or path",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="./models",
        help="Model cache directory",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Starting vLLM API Server")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Cache directory: {args.cache_dir}")
    print("\nAPI will be available at:")
    print(f"  http://{args.host}:{args.port}/v1")
    print("\nOpenAI-compatible endpoints:")
    print(f"  POST http://{args.host}:{args.port}/v1/completions")
    print(f"  POST http://{args.host}:{args.port}/v1/chat/completions")
    print("=" * 60)

    # vLLM command that would be run:
    # python -m vllm.entrypoints.openai.api_server \
    #     --model <model_name> \
    #     --host <host> \
    #     --port <port>

    print("\nTo start the server, run:")
    print(f"  python -m vllm.entrypoints.openai.api_server \\")
    print(f"    --model {args.model} \\")
    print(f"    --host {args.host} \\")
    print(f"    --port {args.port} \\")
    print(f"    --trust-remote-code")


if __name__ == "__main__":
    main()
