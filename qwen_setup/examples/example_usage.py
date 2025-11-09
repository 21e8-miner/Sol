#!/usr/bin/env python3
"""
Example Usage of Qwen Client

This script demonstrates various ways to use the self-hosted Qwen LLM
from Claude Code or any Python environment.
"""

import sys
import os

# Add parent directory to path to import client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import QwenClient


def example_simple_completion():
    """Example 1: Simple text completion"""
    print("\n" + "=" * 60)
    print("Example 1: Simple Text Completion")
    print("=" * 60)

    client = QwenClient(base_url="http://localhost:8000")

    prompt = "Explain self-hosted LLM architecture in 3 bullet points."
    print(f"Prompt: {prompt}\n")

    response = client.complete(prompt, max_tokens=256, temperature=0.7)
    print(f"Response:\n{response}")


def example_chat_conversation():
    """Example 2: Multi-turn chat conversation"""
    print("\n" + "=" * 60)
    print("Example 2: Multi-turn Chat Conversation")
    print("=" * 60)

    client = QwenClient(base_url="http://localhost:8000")

    messages = [
        {
            "role": "user",
            "content": "What are the benefits of self-hosting an LLM?",
        },
    ]

    print(f"User: {messages[0]['content']}\n")
    response = client.chat(messages)
    print(f"Assistant: {response}\n")

    # Follow-up question
    messages.append({"role": "assistant", "content": response})
    messages.append(
        {
            "role": "user",
            "content": "What are the hardware requirements?",
        }
    )

    print(f"User: {messages[-1]['content']}\n")
    response = client.chat(messages)
    print(f"Assistant: {response}")


def example_code_analysis():
    """Example 3: Code analysis"""
    print("\n" + "=" * 60)
    print("Example 3: Code Analysis")
    print("=" * 60)

    client = QwenClient(base_url="http://localhost:8000")

    code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

    question = "How can I optimize this Fibonacci function?"

    print(f"Code:\n{code}")
    print(f"Question: {question}\n")

    response = client.analyze_code(code, question)
    print(f"Analysis:\n{response}")


def example_code_debugging():
    """Example 4: Code debugging assistance"""
    print("\n" + "=" * 60)
    print("Example 4: Code Debugging")
    print("=" * 60)

    client = QwenClient(base_url="http://localhost:8000")

    code = """
numbers = [1, 2, 3, 4, 5]
total = 0
for i in range(len(numbers) + 1):
    total += numbers[i]
print(total)
"""

    error = "IndexError: list index out of range"

    print(f"Code:\n{code}")
    print(f"Error: {error}\n")

    response = client.debug_code(code, error)
    print(f"Debugging Help:\n{response}")


def example_concept_explanation():
    """Example 5: Explain programming concepts"""
    print("\n" + "=" * 60)
    print("Example 5: Concept Explanation")
    print("=" * 60)

    client = QwenClient(base_url="http://localhost:8000")

    concept = "model quantization"
    level = "intermediate"

    print(f"Concept: {concept}")
    print(f"Level: {level}\n")

    response = client.explain_concept(concept, level)
    print(f"Explanation:\n{response}")


def example_batch_processing():
    """Example 6: Batch processing multiple prompts"""
    print("\n" + "=" * 60)
    print("Example 6: Batch Processing")
    print("=" * 60)

    client = QwenClient(base_url="http://localhost:8000")

    prompts = [
        "What is Python?",
        "What is machine learning?",
        "What is an API?",
    ]

    print("Processing multiple prompts...\n")

    for i, prompt in enumerate(prompts, 1):
        print(f"{i}. Prompt: {prompt}")
        response = client.complete(prompt, max_tokens=100, temperature=0.5)
        print(f"   Response: {response}\n")


def example_custom_parameters():
    """Example 7: Using custom parameters"""
    print("\n" + "=" * 60)
    print("Example 7: Custom Parameters")
    print("=" * 60)

    client = QwenClient(base_url="http://localhost:8000")

    prompt = "Write a creative story about AI."

    print("Comparing different temperature settings:\n")

    # Low temperature (more deterministic)
    print("Temperature 0.1 (deterministic):")
    response = client.complete(prompt, max_tokens=100, temperature=0.1)
    print(f"{response}\n")

    # High temperature (more creative)
    print("Temperature 1.5 (creative):")
    response = client.complete(prompt, max_tokens=100, temperature=1.5)
    print(f"{response}")


def example_integration_with_data():
    """Example 8: Integrating with data processing"""
    print("\n" + "=" * 60)
    print("Example 8: Data Processing Integration")
    print("=" * 60)

    client = QwenClient(base_url="http://localhost:8000")

    # Simulate some data
    data = {
        "sales": [100, 150, 200, 180, 220],
        "months": ["Jan", "Feb", "Mar", "Apr", "May"],
    }

    prompt = f"""
Analyze this sales data and provide insights:

Sales by month: {dict(zip(data['months'], data['sales']))}

Provide:
1. Trend analysis
2. Best performing month
3. Recommendations
"""

    print(f"Data: {data}\n")
    print("Requesting analysis...\n")

    response = client.complete(prompt, max_tokens=300)
    print(f"Analysis:\n{response}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("Qwen Self-Hosted LLM - Usage Examples")
    print("=" * 60)
    print("\nMake sure the Qwen API server is running at http://localhost:8000")
    print("Start it with: python serve_api.py")
    print("\nPress Enter to continue or Ctrl+C to exit...")

    try:
        input()
    except KeyboardInterrupt:
        print("\nExiting...")
        return

    # Create client and check health
    try:
        client = QwenClient(base_url="http://localhost:8000")
        health = client.health_check()
        print(f"\n✓ Server is healthy: {health}")
    except Exception as e:
        print(f"\n✗ Cannot connect to server: {e}")
        print("\nPlease start the server first:")
        print("  python serve_api.py")
        return

    # Run examples
    examples = [
        ("Simple Completion", example_simple_completion),
        ("Chat Conversation", example_chat_conversation),
        ("Code Analysis", example_code_analysis),
        ("Code Debugging", example_code_debugging),
        ("Concept Explanation", example_concept_explanation),
        ("Batch Processing", example_batch_processing),
        ("Custom Parameters", example_custom_parameters),
        ("Data Processing", example_integration_with_data),
    ]

    for name, example_func in examples:
        try:
            example_func()
            print("\n" + "-" * 60)
            print(f"✓ {name} completed")
            print("-" * 60)

            # Pause between examples
            print("\nPress Enter for next example or Ctrl+C to exit...")
            input()

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n✗ Error in {name}: {e}")
            print("Continuing to next example...\n")
            continue

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
