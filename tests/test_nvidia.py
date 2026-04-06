"""
NVIDIA API Latency Testing Script
Tests response time, streaming performance, and conversational latency
Using official NVIDIA API calling method with requests library
"""

import os
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# NVIDIA API Configuration
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')
if not NVIDIA_API_KEY:
    raise ValueError("Missing NVIDIA_API_KEY in .env")

INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Test configurations
MODELS_TO_TEST = [
    "google/gemma-4-31b-it",
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
]

TEST_PROMPTS = [
    "What's the weather like?",
    "Tell me a short joke",
    "What's 25 times 17?",
    "Explain quantum computing in one sentence",
    "Write a haiku about AI"
]


class LatencyTester:
    def __init__(self, model_name):
        self.model = model_name
        self.results = []

    def test_single_response(self, prompt, stream=False):
        """Test single prompt-response latency."""
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Accept": "text/event-stream" if stream else "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.7,
            "top_p": 0.95,
            "stream": stream
        }

        start_time = time.perf_counter()

        try:
            response = requests.post(INVOKE_URL, headers=headers, json=payload, stream=stream)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "latency": time.perf_counter() - start_time
                }

            if stream:
                # Measure time to first token and total time
                first_token_time = None
                full_response = ""

                for line in response.iter_lines():
                    if line:
                        line_text = line.decode("utf-8")

                        # Skip empty lines and comments
                        if not line_text.strip() or line_text.startswith(':'):
                            continue

                        # Parse SSE format: "data: {json}"
                        if line_text.startswith('data: '):
                            data_text = line_text[6:]  # Remove "data: " prefix

                            # Check for end signal
                            if data_text.strip() == '[DONE]':
                                break

                            try:
                                data = json.loads(data_text)
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')

                                    if content:
                                        if first_token_time is None:
                                            first_token_time = time.perf_counter() - start_time
                                        full_response += content
                            except json.JSONDecodeError:
                                continue

                total_time = time.perf_counter() - start_time

                return {
                    "success": True,
                    "time_to_first_token": first_token_time or total_time,
                    "total_time": total_time,
                    "response_length": len(full_response),
                    "response": full_response[:100] + "..." if len(full_response) > 100 else full_response
                }
            else:
                # Non-streaming
                data = response.json()
                end_time = time.perf_counter()
                latency = end_time - start_time

                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    return {
                        "success": True,
                        "latency": latency,
                        "response_length": len(content),
                        "response": content[:100] + "..." if len(content) > 100 else content
                    }
                else:
                    return {
                        "success": False,
                        "error": "No response content",
                        "latency": latency
                    }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency": time.perf_counter() - start_time
            }

    def test_conversation(self, num_turns=3):
        """Test multi-turn conversation latency."""
        conversation_history = []
        turn_latencies = []

        prompts = [
            "Hi, what's your name?",
            "What can you help me with?",
            "Tell me something interesting about AI"
        ][:num_turns]

        print(f"\n{'='*60}")
        print(f"Testing {num_turns}-turn conversation...")
        print(f"{'='*60}")

        for i, prompt in enumerate(prompts):
            print(f"\n[Turn {i+1}] User: {prompt}")

            conversation_history.append({"role": "user", "content": prompt})

            headers = {
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Accept": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": conversation_history,
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 0.95,
                "stream": False
            }

            start_time = time.perf_counter()

            try:
                response = requests.post(INVOKE_URL, headers=headers, json=payload)
                latency = time.perf_counter() - start_time

                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        assistant_message = data['choices'][0]['message']['content']
                        conversation_history.append({"role": "assistant", "content": assistant_message})
                        turn_latencies.append(latency)
                        print(f"[Turn {i+1}] AI ({latency:.3f}s): {assistant_message[:150]}...")
                    else:
                        print(f"[Turn {i+1}] ERROR: No response content")
                        turn_latencies.append(None)
                else:
                    print(f"[Turn {i+1}] ERROR: HTTP {response.status_code}")
                    turn_latencies.append(None)

            except Exception as e:
                print(f"[Turn {i+1}] ERROR: {e}")
                turn_latencies.append(None)

        return {
            "success": True,
            "turn_latencies": turn_latencies,
            "avg_latency": sum(l for l in turn_latencies if l) / len([l for l in turn_latencies if l]) if turn_latencies else 0,
            "total_turns": num_turns
        }

    def run_benchmark(self):
        """Run full benchmark suite."""
        print(f"\n{'='*60}")
        print(f"NVIDIA API LATENCY BENCHMARK")
        print(f"Model: {self.model}")
        print(f"{'='*60}\n")

        # Test 1: Non-streaming responses
        print("TEST 1: Non-Streaming Responses")
        print("-" * 60)
        non_streaming_latencies = []

        for i, prompt in enumerate(TEST_PROMPTS, 1):
            print(f"\n[{i}/{len(TEST_PROMPTS)}] Testing: \"{prompt}\"")
            result = self.test_single_response(prompt, stream=False)

            if result["success"]:
                latency = result["latency"]
                non_streaming_latencies.append(latency)
                print(f"  ✓ Latency: {latency:.3f}s")
                print(f"  Response: {result['response']}")
            else:
                print(f"  ✗ Error: {result['error']}")

        # Test 2: Streaming responses
        print(f"\n{'='*60}")
        print("TEST 2: Streaming Responses (Time to First Token)")
        print("-" * 60)
        streaming_ttft = []
        streaming_total = []

        for i, prompt in enumerate(TEST_PROMPTS[:3], 1):  # Test first 3 for streaming
            print(f"\n[{i}/3] Testing: \"{prompt}\"")
            result = self.test_single_response(prompt, stream=True)

            if result["success"]:
                ttft = result["time_to_first_token"]
                total = result["total_time"]
                streaming_ttft.append(ttft)
                streaming_total.append(total)
                print(f"  ✓ Time to First Token: {ttft:.3f}s")
                print(f"  ✓ Total Time: {total:.3f}s")
                print(f"  Response: {result['response']}")
            else:
                print(f"  ✗ Error: {result.get('error', 'Unknown error')}")

        # Test 3: Conversational latency
        conv_result = self.test_conversation(num_turns=3)

        # Summary
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")

        if non_streaming_latencies:
            avg_latency = sum(non_streaming_latencies) / len(non_streaming_latencies)
            min_latency = min(non_streaming_latencies)
            max_latency = max(non_streaming_latencies)

            print(f"\nNon-Streaming Performance:")
            print(f"  Average Latency: {avg_latency:.3f}s")
            print(f"  Min Latency: {min_latency:.3f}s")
            print(f"  Max Latency: {max_latency:.3f}s")

        if streaming_ttft:
            avg_ttft = sum(streaming_ttft) / len(streaming_ttft)
            avg_total = sum(streaming_total) / len(streaming_total)

            print(f"\nStreaming Performance:")
            print(f"  Average Time to First Token: {avg_ttft:.3f}s")
            print(f"  Average Total Time: {avg_total:.3f}s")

        if conv_result["success"]:
            print(f"\nConversational Performance:")
            print(f"  Average Turn Latency: {conv_result['avg_latency']:.3f}s")
            print(f"  Total Turns Tested: {conv_result['total_turns']}")

        print(f"\n{'='*60}\n")

        return {
            "model": self.model,
            "non_streaming": {
                "latencies": non_streaming_latencies,
                "avg": sum(non_streaming_latencies) / len(non_streaming_latencies) if non_streaming_latencies else 0,
                "min": min(non_streaming_latencies) if non_streaming_latencies else 0,
                "max": max(non_streaming_latencies) if non_streaming_latencies else 0
            },
            "streaming": {
                "ttft": streaming_ttft,
                "total": streaming_total,
                "avg_ttft": sum(streaming_ttft) / len(streaming_ttft) if streaming_ttft else 0,
                "avg_total": sum(streaming_total) / len(streaming_total) if streaming_total else 0
            },
            "conversation": conv_result
        }


def test_model_availability():
    """Test which models are available."""
    print("Testing NVIDIA API connection...\n")

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json"
    }

    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10
    }

    try:
        response = requests.post(INVOKE_URL, headers=headers, json=payload, timeout=10)

        if response.status_code == 200:
            print("✓ Successfully connected to NVIDIA API\n")
            print("Recommended models:")
            for model in MODELS_TO_TEST:
                print(f"  - {model}")
            return True
        else:
            print(f"✗ Connection failed: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False


def quick_test():
    """Quick single test for immediate feedback."""
    print("\n" + "="*60)
    print("QUICK LATENCY TEST")
    print("="*60 + "\n")

    model = "meta/llama-3.1-8b-instruct"  # Fast model for quick test
    prompt = "Say hello in one short sentence."

    print(f"Model: {model}")
    print(f"Prompt: {prompt}\n")

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json"
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50,
        "temperature": 0.7,
        "stream": False
    }

    start = time.perf_counter()

    try:
        response = requests.post(INVOKE_URL, headers=headers, json=payload)
        latency = time.perf_counter() - start

        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                message = data['choices'][0]['message']['content']
                print(f"✓ Response received in {latency:.3f}s")
                print(f"\nResponse: {message}")
                print("\n" + "="*60 + "\n")
                return True
            else:
                print(f"✗ No response content")
                return False
        else:
            print(f"✗ HTTP Error {response.status_code}: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Main test runner."""
    print("\n" + "="*70)
    print("NVIDIA API LATENCY TESTING SUITE")
    print("="*70 + "\n")

    # Test connection
    if not test_model_availability():
        print("\n⚠️  Could not connect to NVIDIA API. Check your API key.")
        return

    print("\n" + "="*70)
    print("Select test mode:")
    print("  1. Quick test (single request, fast)")
    print("  2. Full benchmark (comprehensive, ~2-3 minutes)")
    print("  3. Compare models (test multiple models)")
    print("="*70)

    choice = input("\nEnter choice (1-3, or 'q' to quit): ").strip()

    if choice == '1':
        quick_test()

    elif choice == '2':
        model = input(f"\nEnter model name (default: meta/llama-3.1-8b-instruct): ").strip()
        if not model:
            model = "meta/llama-3.1-8b-instruct"

        tester = LatencyTester(model)
        results = tester.run_benchmark()

        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"nvidia_benchmark_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {filename}")

    elif choice == '3':
        print("\nTesting multiple models (this may take 5-10 minutes)...\n")
        all_results = []

        for model in MODELS_TO_TEST[:2]:  # Test first 2 models
            print(f"\n{'#'*70}")
            print(f"Testing: {model}")
            print(f"{'#'*70}")

            tester = LatencyTester(model)
            results = tester.run_benchmark()
            all_results.append(results)

            time.sleep(2)  # Brief pause between models

        # Comparison summary
        print("\n" + "="*70)
        print("MODEL COMPARISON SUMMARY")
        print("="*70 + "\n")

        for result in all_results:
            print(f"{result['model']}:")
            print(f"  Avg Latency: {result['non_streaming']['avg']:.3f}s")
            print(f"  Avg TTFT: {result['streaming']['avg_ttft']:.3f}s")
            print(f"  Conversation Avg: {result['conversation']['avg_latency']:.3f}s")
            print()

        # Save comparison
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"nvidia_comparison_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"Comparison results saved to: {filename}")

    else:
        print("Exiting...")


if __name__ == "__main__":
    main()
