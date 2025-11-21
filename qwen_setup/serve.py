#!/usr/bin/env python3
"""
Simple FastAPI server for Qwen LLM
Provides OpenAI-compatible endpoints for the self-hosted model
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os
from typing import Optional

print("=" * 60)
print("🚀 Qwen LLM API Server")
print("=" * 60)

# Configuration
MODEL_NAME = "Qwen/Qwen2-1.5B-Instruct"
CACHE_DIR = "./models"
PORT = 8000

print(f"📦 Loading model: {MODEL_NAME}")
print(f"💾 Cache directory: {os.path.abspath(CACHE_DIR)}")

# Load model and tokenizer
print("⏳ Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
print("✅ Tokenizer loaded")

print("⏳ Loading model weights (~2.9GB)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    cache_dir=CACHE_DIR,
    torch_dtype=torch.float32,  # CPU mode
    device_map="cpu"
)
print("✅ Model loaded successfully!")

total_params = sum(p.numel() for p in model.parameters()) / 1e9
print(f"📊 Model size: {total_params:.2f}B parameters")
print(f"🖥️  Device: CPU")
print("=" * 60)

app = FastAPI(title="Qwen LLM API", version="1.0")

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    top_p: float = 0.9

class GenerateResponse(BaseModel):
    text: str
    tokens_generated: int

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "device": "cpu",
        "parameters": f"{total_params:.2f}B"
    }

@app.get("/models")
def list_models():
    """List available models"""
    return {
        "models": [MODEL_NAME]
    }

@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    """Generate text completion"""
    try:
        # Tokenize input
        inputs = tokenizer(request.prompt, return_tensors="pt")

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )

        # Decode output
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        tokens_generated = len(outputs[0]) - len(inputs['input_ids'][0])

        return GenerateResponse(
            text=generated_text,
            tokens_generated=tokens_generated
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

if __name__ == "__main__":
    print("\n🌐 Starting server...")
    print(f"📡 Server URL: http://localhost:{PORT}")
    print(f"🔍 Health check: http://localhost:{PORT}/health")
    print(f"📚 API docs: http://localhost:{PORT}/docs")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
