#!/usr/bin/env python3
"""
Qwen Model Download Script

This script downloads the Qwen model from Hugging Face and prepares it for local inference.
Supports multiple model sizes and optional quantization.
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
except ImportError:
    print("Error: Required packages not installed. Please run:")
    print("  pip install -r requirements.txt")
    sys.exit(1)


# Available Qwen models
AVAILABLE_MODELS = {
    "qwen-1.8b": "Qwen/Qwen-1_8B-Chat",
    "qwen-7b": "Qwen/Qwen-7B-Chat",
    "qwen-14b": "Qwen/Qwen-14B-Chat",
    "qwen-72b": "Qwen/Qwen-72B-Chat",
    "qwen2-0.5b": "Qwen/Qwen2-0.5B-Instruct",
    "qwen2-1.5b": "Qwen/Qwen2-1.5B-Instruct",
    "qwen2-7b": "Qwen/Qwen2-7B-Instruct",
    "qwen2-72b": "Qwen/Qwen2-72B-Instruct",
}


def download_model(
    model_name: str,
    cache_dir: str = "./models",
    use_8bit: bool = False,
    use_4bit: bool = False,
    download_only: bool = False,
):
    """
    Download and optionally load a Qwen model.

    Args:
        model_name: Name of the model (e.g., 'qwen-7b')
        cache_dir: Directory to cache the model
        use_8bit: Use 8-bit quantization (requires bitsandbytes)
        use_4bit: Use 4-bit quantization (requires bitsandbytes)
        download_only: Only download, don't load into memory
    """
    if model_name not in AVAILABLE_MODELS:
        print(f"Error: Model '{model_name}' not found.")
        print(f"Available models: {', '.join(AVAILABLE_MODELS.keys())}")
        sys.exit(1)

    model_id = AVAILABLE_MODELS[model_name]
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading model: {model_id}")
    print(f"Cache directory: {cache_path.absolute()}")
    print("-" * 60)

    # Download tokenizer
    print("Downloading tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            cache_dir=cache_dir,
            trust_remote_code=True,
        )
        print(f"✓ Tokenizer downloaded successfully")
    except Exception as e:
        print(f"✗ Error downloading tokenizer: {e}")
        sys.exit(1)

    # Download model
    print(f"\nDownloading model weights (this may take a while)...")

    try:
        load_kwargs = {
            "pretrained_model_name_or_path": model_id,
            "cache_dir": cache_dir,
            "trust_remote_code": True,
        }

        if download_only:
            # Just download, don't load into memory
            load_kwargs["low_cpu_mem_usage"] = True
            load_kwargs["torch_dtype"] = torch.float16
        else:
            # Check for GPU
            if torch.cuda.is_available():
                print(f"GPU detected: {torch.cuda.get_device_name(0)}")
                load_kwargs["device_map"] = "auto"
                load_kwargs["torch_dtype"] = torch.float16
            else:
                print("No GPU detected. Using CPU (will be slow).")
                load_kwargs["torch_dtype"] = torch.float32
                load_kwargs["low_cpu_mem_usage"] = True

            # Apply quantization if requested
            if use_8bit:
                print("Using 8-bit quantization...")
                load_kwargs["load_in_8bit"] = True
            elif use_4bit:
                print("Using 4-bit quantization...")
                load_kwargs["load_in_4bit"] = True

        model = AutoModelForCausalLM.from_pretrained(**load_kwargs)
        print(f"✓ Model downloaded successfully")

        if not download_only:
            # Test the model
            print("\nTesting model...")
            test_prompt = "Hello! Please introduce yourself."
            inputs = tokenizer(test_prompt, return_tensors="pt")

            if torch.cuda.is_available() and not use_8bit and not use_4bit:
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_length=50,
                    num_return_sequences=1,
                )

            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(f"\nTest output:\n{response}\n")
            print("✓ Model test successful!")

    except Exception as e:
        print(f"✗ Error downloading/loading model: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Model setup complete!")
    print("=" * 60)
    print(f"Model: {model_id}")
    print(f"Location: {cache_path.absolute()}")
    print("\nNext steps:")
    print("1. Start the API server: python serve_api.py")
    print("2. Test the client: python client.py")


def main():
    parser = argparse.ArgumentParser(
        description="Download Qwen model for local inference"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen2-1.5b",
        help=f"Model to download. Options: {', '.join(AVAILABLE_MODELS.keys())}",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="./models",
        help="Directory to cache the model (default: ./models)",
    )
    parser.add_argument(
        "--8bit",
        action="store_true",
        help="Use 8-bit quantization (requires GPU and bitsandbytes)",
    )
    parser.add_argument(
        "--4bit",
        action="store_true",
        help="Use 4-bit quantization (requires GPU and bitsandbytes)",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download the model, don't load it into memory",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models and exit",
    )

    args = parser.parse_args()

    if args.list:
        print("Available Qwen models:")
        for key, value in AVAILABLE_MODELS.items():
            print(f"  {key:15} -> {value}")
        sys.exit(0)

    download_model(
        model_name=args.model,
        cache_dir=args.cache_dir,
        use_8bit=args.__dict__.get("8bit", False),
        use_4bit=args.__dict__.get("4bit", False),
        download_only=args.download_only,
    )


if __name__ == "__main__":
    main()
