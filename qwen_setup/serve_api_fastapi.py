#!/usr/bin/env python3
"""
Qwen API Server using FastAPI

Custom API server that works with both CPU and GPU.
Provides OpenAI-compatible endpoints for chat completions.
"""

import argparse
import logging
import os
import sys
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import torch
from pydantic import BaseModel, Field

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse, StreamingResponse
    import uvicorn
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
except ImportError:
    print("Error: Required packages not installed. Install with:")
    print("  pip install fastapi uvicorn transformers torch")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model and tokenizer
model = None
tokenizer = None
model_config = {}


# Request/Response models
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "qwen"
    messages: List[Message]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    stream: bool = False


class CompletionRequest(BaseModel):
    model: str = "qwen"
    prompt: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-qwen"
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup and cleanup on shutdown"""
    global model, tokenizer, model_config

    logger.info("Loading model...")
    logger.info(f"Model path: {model_config['model_path']}")
    logger.info(f"Device: {model_config['device']}")

    try:
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_config["model_path"],
            cache_dir=model_config.get("cache_dir"),
            trust_remote_code=True,
        )

        # Load model
        load_kwargs = {
            "pretrained_model_name_or_path": model_config["model_path"],
            "cache_dir": model_config.get("cache_dir"),
            "trust_remote_code": True,
        }

        if model_config["device"] == "cuda":
            load_kwargs["device_map"] = "auto"
            load_kwargs["torch_dtype"] = torch.float16
        else:
            load_kwargs["torch_dtype"] = torch.float32
            load_kwargs["low_cpu_mem_usage"] = True

        model = AutoModelForCausalLM.from_pretrained(**load_kwargs)

        if model_config["device"] == "cpu":
            model = model.to("cpu")

        logger.info("Model loaded successfully!")

    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Qwen API Server",
    description="OpenAI-compatible API for Qwen models",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Qwen API Server",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "completion": "/v1/completions",
            "models": "/v1/models",
            "health": "/health",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "device": model_config.get("device", "unknown"),
    }


@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": model_config.get("model_path", "qwen"),
                "object": "model",
                "created": 1234567890,
                "owned_by": "local",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint
    """
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Convert messages to prompt
        # For Qwen chat models, use the chat template if available
        if hasattr(tokenizer, "apply_chat_template"):
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            # Fallback: simple concatenation
            prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
            prompt += "\nassistant: "

        # Tokenize
        inputs = tokenizer(prompt, return_tensors="pt")

        if model_config["device"] == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=request.temperature > 0,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )

        # Decode
        response_text = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )

        # Format response
        import time
        return {
            "id": "chatcmpl-qwen",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": inputs["input_ids"].shape[1],
                "completion_tokens": outputs.shape[1] - inputs["input_ids"].shape[1],
                "total_tokens": outputs.shape[1],
            },
        }

    except Exception as e:
        logger.error(f"Error in chat_completions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/completions")
async def completions(request: CompletionRequest):
    """
    OpenAI-compatible completions endpoint
    """
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Tokenize
        inputs = tokenizer(request.prompt, return_tensors="pt")

        if model_config["device"] == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=request.temperature > 0,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )

        # Decode
        response_text = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )

        # Format response
        import time
        return {
            "id": "cmpl-qwen",
            "object": "text_completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "text": response_text,
                    "index": 0,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": inputs["input_ids"].shape[1],
                "completion_tokens": outputs.shape[1] - inputs["input_ids"].shape[1],
                "total_tokens": outputs.shape[1],
            },
        }

    except Exception as e:
        logger.error(f"Error in completions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate(request: Dict[str, Any]):
    """
    Simple generate endpoint (non-OpenAI format)
    """
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        prompt = request.get("prompt", "")
        max_tokens = request.get("max_tokens", 512)
        temperature = request.get("temperature", 0.7)

        inputs = tokenizer(prompt, return_tensors="pt")

        if model_config["device"] == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )

        response_text = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )

        return {
            "generated_text": response_text,
            "prompt": prompt,
        }

    except Exception as e:
        logger.error(f"Error in generate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    parser = argparse.ArgumentParser(description="Start Qwen API server")
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
        help="Host to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="./models",
        help="Model cache directory",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Device to use (auto, cuda, or cpu)",
    )

    args = parser.parse_args()

    # Determine device
    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device

    # Set global config
    global model_config
    model_config = {
        "model_path": args.model,
        "cache_dir": args.cache_dir,
        "device": device,
    }

    logger.info("=" * 60)
    logger.info("Starting Qwen API Server")
    logger.info("=" * 60)
    logger.info(f"Model: {args.model}")
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Device: {device}")
    logger.info(f"Cache directory: {args.cache_dir}")
    logger.info("=" * 60)

    # Start server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
