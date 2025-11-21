#!/usr/bin/env python3
"""
Simple Synchronous FastAPI server for Qwen LLM
Loads model first, then starts server. Avoids potential async loading issues.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import os
from typing import Optional
import time

print("=" * 60)
print("🚀 Qwen LLM API Server (Synchronous Load)")
print("=" * 60)

# Configuration
MODEL_NAME = "Qwen/Qwen2-1.5B-Instruct"
CACHE_DIR = "./models"
DEVICE = "cpu"  # Explicitly set to CPU

print(f"Loading Model: {MODEL_NAME}")
print(f"Cache Directory: {CACHE_DIR}")
print(f"Device: {DEVICE}")
print("-" * 60)

# --- Load Model First ---
start_time = time.time()
try:
    print("⏳ Loading Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=CACHE_DIR)
    print("✅ Tokenizer loaded.")

    print("⏳ Loading Model weights (this may take 30-60 seconds)...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        cache_dir=CACHE_DIR,
        torch_dtype=torch.float32,  # Use float32 for CPU stability
        device_map=DEVICE,
        low_cpu_mem_usage=True  # Helps with memory on constrained systems
    )
    print("✅ Model loaded successfully.")

    # Test the model briefly
    test_inputs = tokenizer("Testing 1 2 3.", return_tensors="pt")
    with torch.no_grad():  # Disable gradient calculation for inference
        test_outputs = model.generate(**test_inputs, max_new_tokens=5, do_sample=False)
    test_result = tokenizer.decode(test_outputs[0], skip_special_tokens=True)
    print(f"✅ Model test run OK: '{test_result[:50]}...'")
    print("-" * 60)

    load_time = time.time() - start_time
    total_params = sum(p.numel() for p in model.parameters()) / 1e9
    print(f"📊 Model: {total_params:.2f}B parameters")
    print(f"⏱️  Loaded in {load_time:.2f} seconds")
    print("-" * 60)

except Exception as e:
    print(f"❌ FATAL: Failed to load model: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# --- Create FastAPI App ---
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
        "device": DEVICE,
        "parameters": f"{total_params:.2f}B"
    }

@app.get("/models")
def list_models():
    """List available models"""
    return {"models": [MODEL_NAME]}

@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    """Generate text completion"""
    try:
        # Tokenize input
        inputs = tokenizer(request.prompt, return_tensors="pt")

        # Generate
        start = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=True if request.temperature > 0 else False,
                pad_token_id=tokenizer.eos_token_id
            )

        latency = (time.time() - start) * 1000

        # Decode output
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        tokens_generated = len(outputs[0]) - len(inputs['input_ids'][0])

        print(f"Generated {tokens_generated} tokens in {latency:.0f}ms")

        return GenerateResponse(
            text=generated_text,
            tokens_generated=tokens_generated
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

if __name__ == "__main__":
    PORT = 8000
    print("\n🌐 Starting server...")
    print(f"📡 Server URL: http://localhost:{PORT}")
    print(f"🔍 Health check: http://localhost:{PORT}/health")
    print(f"📚 API docs: http://localhost:{PORT}/docs")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)
    print()

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
