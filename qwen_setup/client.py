#!/usr/bin/env python3
"""
Qwen Client Library
Easy-to-use client for interacting with self-hosted Qwen API
"""

import requests
from typing import Dict, Optional

class QwenClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def health_check(self) -> bool:
        """Check if server is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200 and response.json().get("status") == "ok"
        except:
            return False

    def list_models(self) -> Dict:
        """Get list of available models"""
        try:
            response = self.session.get(f"{self.base_url}/models", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Failed to list models: {e}")

    def complete(self,
                 prompt: str,
                 max_tokens: int = 256,
                 temperature: float = 0.7,
                 top_p: float = 0.9) -> str:
        """Generate text completion"""
        try:
            response = self.session.post(
                f"{self.base_url}/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p
                },
                timeout=60  # Long timeout for generation
            )
            response.raise_for_status()
            return response.json()["text"]
        except Exception as e:
            raise Exception(f"Failed to generate: {e}")

    def chat(self, messages: list, max_tokens: int = 256) -> str:
        """Chat completion (converts messages to prompt)"""
        # Simple message formatting
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
            elif role == "system":
                prompt += f"System: {content}\n"
        prompt += "Assistant:"

        return self.complete(prompt, max_tokens=max_tokens)

if __name__ == "__main__":
    # Test the client
    import sys

    client = QwenClient()

    print("🔍 Testing Qwen client...")

    # Health check
    print("\n1️⃣ Health check...")
    if client.health_check():
        print("✅ Server is healthy!")
    else:
        print("❌ Server is not responding. Make sure to start the server with: python serve.py")
        sys.exit(1)

    # List models
    print("\n2️⃣ Available models...")
    models = client.list_models()
    print(f"✅ Models: {models}")

    # Test completion
    print("\n3️⃣ Test completion...")
    prompt = "What is 2+2? Answer briefly:"
    print(f"Prompt: {prompt}")
    response = client.complete(prompt, max_tokens=50)
    print(f"Response: {response}")

    print("\n✅ All tests passed!")
