#!/usr/bin/env python3
"""
Qwen Client Library

Easy-to-use client for interacting with self-hosted Qwen API.
Compatible with both OpenAI-style and custom endpoints.
"""

import argparse
import json
import sys
from typing import List, Dict, Optional, Any

try:
    import requests
except ImportError:
    print("Error: requests not installed. Install with:")
    print("  pip install requests")
    sys.exit(1)


class QwenClient:
    """
    Client for interacting with Qwen API server.

    Examples:
        # Create client
        client = QwenClient(base_url="http://localhost:8000")

        # Simple completion
        response = client.complete("Explain quantum computing in simple terms.")
        print(response)

        # Chat conversation
        messages = [
            {"role": "user", "content": "What is Python?"},
        ]
        response = client.chat(messages)
        print(response)

        # Streaming response
        for chunk in client.chat_stream(messages):
            print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 60,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Qwen client.

        Args:
            base_url: Base URL of the API server
            timeout: Request timeout in seconds
            api_key: Optional API key (if server requires authentication)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        stream: bool = False,
    ) -> requests.Response:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                timeout=self.timeout,
                stream=stream,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to API server at {self.base_url}. "
                "Make sure the server is running."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request timed out after {self.timeout} seconds")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"API error: {e.response.text}")

    def health_check(self) -> Dict[str, Any]:
        """Check if the API server is healthy"""
        response = self._request("GET", "/health")
        return response.json()

    def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        response = self._request("GET", "/v1/models")
        return response.json()["data"]

    def complete(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        model: str = "qwen",
    ) -> str:
        """
        Simple text completion.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            model: Model name

        Returns:
            Generated text
        """
        try:
            # Try OpenAI-compatible endpoint
            response = self._request(
                "POST",
                "/v1/completions",
                json_data={
                    "model": model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                },
            )
            result = response.json()
            return result["choices"][0]["text"]
        except:
            # Fallback to simple /generate endpoint
            response = self._request(
                "POST",
                "/generate",
                json_data={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            result = response.json()
            return result.get("generated_text", "")

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        model: str = "qwen",
    ) -> str:
        """
        Chat completion.

        Args:
            messages: List of messages with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            model: Model name

        Returns:
            Assistant's response
        """
        response = self._request(
            "POST",
            "/v1/chat/completions",
            json_data={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
            },
        )
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        model: str = "qwen",
    ):
        """
        Streaming chat completion.

        Args:
            messages: List of messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            model: Model name

        Yields:
            Response chunks as they arrive
        """
        # Note: Streaming support depends on server implementation
        # This is a placeholder for future streaming support
        response = self.chat(messages, max_tokens, temperature, model=model)
        yield response

    def analyze_code(self, code: str, question: str) -> str:
        """
        Analyze code and answer questions about it.

        Args:
            code: Code snippet to analyze
            question: Question about the code

        Returns:
            Analysis response
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful code analysis assistant.",
            },
            {
                "role": "user",
                "content": f"Code:\n```\n{code}\n```\n\nQuestion: {question}",
            },
        ]
        return self.chat(messages)

    def debug_code(self, code: str, error: str) -> str:
        """
        Help debug code given an error message.

        Args:
            code: Code with the bug
            error: Error message

        Returns:
            Debugging suggestions
        """
        messages = [
            {
                "role": "system",
                "content": "You are an expert debugging assistant.",
            },
            {
                "role": "user",
                "content": f"Code:\n```\n{code}\n```\n\nError:\n{error}\n\nHow can I fix this?",
            },
        ]
        return self.chat(messages)

    def explain_concept(self, concept: str, level: str = "beginner") -> str:
        """
        Explain a programming concept.

        Args:
            concept: Concept to explain
            level: Difficulty level (beginner, intermediate, advanced)

        Returns:
            Explanation
        """
        messages = [
            {
                "role": "user",
                "content": f"Explain {concept} at a {level} level.",
            },
        ]
        return self.chat(messages)


def interactive_mode(client: QwenClient):
    """Run in interactive mode"""
    print("=" * 60)
    print("Qwen Interactive Chat")
    print("=" * 60)
    print("Commands:")
    print("  /quit or /exit - Exit the chat")
    print("  /clear - Clear conversation history")
    print("  /help - Show this help message")
    print("=" * 60)
    print()

    messages = []

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input in ["/quit", "/exit"]:
                print("Goodbye!")
                break

            if user_input == "/clear":
                messages = []
                print("Conversation cleared.")
                continue

            if user_input == "/help":
                print("Commands:")
                print("  /quit or /exit - Exit the chat")
                print("  /clear - Clear conversation history")
                print("  /help - Show this help message")
                continue

            # Add user message
            messages.append({"role": "user", "content": user_input})

            # Get response
            print("Assistant: ", end="", flush=True)
            response = client.chat(messages)
            print(response)
            print()

            # Add assistant message
            messages.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Qwen API Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive chat
  python client.py --interactive

  # Simple completion
  python client.py --prompt "Explain machine learning"

  # Chat with context
  python client.py --chat "What is Python?" "It's a programming language" "What's it used for?"

  # Check server health
  python client.py --health
        """,
    )

    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="API server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        help="Prompt for simple completion",
    )
    parser.add_argument(
        "--chat",
        "-c",
        nargs="+",
        help="Chat messages (alternating user/assistant)",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Check server health",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens to generate (default: 512)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (default: 0.7)",
    )

    args = parser.parse_args()

    # Create client
    client = QwenClient(base_url=args.url)

    try:
        if args.health:
            health = client.health_check()
            print("Server Health:")
            print(json.dumps(health, indent=2))
            return

        if args.list_models:
            models = client.list_models()
            print("Available Models:")
            for model in models:
                print(f"  - {model['id']}")
            return

        if args.interactive:
            interactive_mode(client)
            return

        if args.prompt:
            response = client.complete(
                args.prompt,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            print(response)
            return

        if args.chat:
            messages = [
                {"role": "user" if i % 2 == 0 else "assistant", "content": msg}
                for i, msg in enumerate(args.chat)
            ]
            response = client.chat(
                messages,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            print(response)
            return

        # Default: show help
        parser.print_help()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
