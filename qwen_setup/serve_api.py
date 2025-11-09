#!/usr/bin/env python3
"""
Qwen API Server Launcher

Wrapper script to start the appropriate API server based on your setup.
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Launch Qwen API server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start FastAPI server (works on CPU and GPU)
  python serve_api.py --backend fastapi --model Qwen/Qwen2-1.5B-Instruct

  # Start vLLM server (requires GPU)
  python serve_api.py --backend vllm --model Qwen/Qwen2-7B-Instruct

  # Use a local model path
  python serve_api.py --backend fastapi --model ./models/Qwen2-1.5B-Instruct
        """,
    )

    parser.add_argument(
        "--backend",
        type=str,
        default="fastapi",
        choices=["fastapi", "vllm"],
        help="Backend to use (default: fastapi)",
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
        help="Model cache directory (default: ./models)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Qwen API Server Launcher")
    print("=" * 60)
    print(f"Backend: {args.backend}")
    print(f"Model: {args.model}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print("=" * 60)
    print()

    if args.backend == "fastapi":
        cmd = [
            sys.executable,
            "serve_api_fastapi.py",
            "--model", args.model,
            "--host", args.host,
            "--port", str(args.port),
            "--cache-dir", args.cache_dir,
        ]
    elif args.backend == "vllm":
        # Check if GPU is available
        try:
            import torch
            if not torch.cuda.is_available():
                print("WARNING: No GPU detected. vLLM requires a GPU.")
                print("Consider using --backend fastapi instead.")
                response = input("Continue anyway? [y/N]: ")
                if response.lower() != 'y':
                    sys.exit(0)
        except ImportError:
            pass

        cmd = [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model", args.model,
            "--host", args.host,
            "--port", str(args.port),
            "--trust-remote-code",
        ]
    else:
        print(f"Unknown backend: {args.backend}")
        sys.exit(1)

    print(f"Running command: {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except subprocess.CalledProcessError as e:
        print(f"Error: Server exited with code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Could not find {cmd[0]}")
        print("Make sure you've installed the required dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
