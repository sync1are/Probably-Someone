"""
ARIA Comprehensive Test Suite & Benchmark
Tests all functionality and generates detailed performance report
"""

import os
import sys
import time
import json
import toml
import traceback
from datetime import datetime
from typing import Dict, List, Tuple
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Import all modules to test
try:
    from src.config import (
        OLLAMA_API_KEY, OLLAMA_HOST, DEFAULT_MODEL, VISION_MODEL,
        SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI,
        TTS_VOICE, TTS_SPEED, SYSTEM_PROMPT
    )
    from src.core.llm_client import LLMClient
    from src.core.audio_engine import AudioEngine, StreamingTextProcessor
    from src.tools.registry import execute_tool, TOOL_HANDLERS
    from src.tools.system_tools import (
        take_screenshot, get_clipboard, set_clipboard,
        get_active_window
    )
    from src.tools.web_tools import scrape_webpage
    from src.tools.spotify_tools import (
        spotify_play, spotify_pause, spotify_current_track,
        spotify_skip_next, spotify_skip_previous, get_spotify_client
    )
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)


class TestResult:
    """Store test results with timing and status."""
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.passed = False
        self.duration = 0.0
        self.error = None
        self.details = {}
        self.warnings = []

    def to_dict(self):
        """Convert to JSON-serializable dict."""
        details_copy = {}
        for key, value in self.details.items():
            try:
                # Test if value is JSON serializable
                json.dumps(value)
                details_copy[key] = value
            except (TypeError, ValueError):
                # Convert to string if not serializable
                details_copy[key] = str(value)

        return {
            "name": self.name,
            "category": self.category,
            "passed": self.passed,
            "duration": round(self.duration, 3),
            "error": str(self.error) if self.error else None,
            "details": details_copy,
            "warnings": self.warnings
        }


class ARIATestSuite:
    """Comprehensive test suite for ARIA voice assistant."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None

    def run_test(self, name: str, category: str, test_func, *args, **kwargs) -> TestResult:
        """Run a single test and record results."""
        result = TestResult(name, category)
        print(f"\n  Testing: {name}...", end=" ")

        start = time.perf_counter()
        try:
            test_output = test_func(*args, **kwargs)
            result.duration = time.perf_counter() - start

            # Check if test returned success status
            if isinstance(test_output, dict):
                result.passed = test_output.get('success', True)
                result.details = test_output
                if 'warning' in test_output:
                    result.warnings.append(test_output['warning'])
            else:
                result.passed = bool(test_output)
                result.details = {'result': test_output}

            if result.passed:
                print(f"✓ ({result.duration:.3f}s)")
            else:
                print(f"✗ FAILED ({result.duration:.3f}s)")

        except Exception as e:
            result.duration = time.perf_counter() - start
            result.passed = False
            result.error = e
            print(f"✗ ERROR ({result.duration:.3f}s)")
            print(f"    {str(e)}")

        self.results.append(result)
        return result

    # ==================== CONFIGURATION TESTS ====================

    def test_environment_variables(self):
        """Test all required environment variables are set."""
        print("\n" + "="*70)
        print("CONFIGURATION TESTS")
        print("="*70)

        def check_env():
            missing = []
            present = {}

            # Required variables
            required = {
                'OLLAMA_API_KEY': OLLAMA_API_KEY,
                'SPOTIPY_CLIENT_ID': SPOTIPY_CLIENT_ID,
                'SPOTIPY_CLIENT_SECRET': SPOTIPY_CLIENT_SECRET,
            }

            for key, value in required.items():
                if not value:
                    missing.append(key)
                else:
                    present[key] = "SET"

            # Optional variables
            optional = {
                'NVIDIA_API_KEY': os.getenv('NVIDIA_API_KEY'),
                'SPOTIPY_REDIRECT_URI': SPOTIPY_REDIRECT_URI
            }

            for key, value in optional.items():
                present[key] = "SET" if value else "NOT SET (optional)"

            return {
                'success': len(missing) == 0,
                'present': present,
                'missing': missing
            }

        self.run_test("Environment Variables", "Configuration", check_env)

    def test_configuration_values(self):
        """Test configuration values are valid."""
        def check_config():
            issues = []
            config = {}

            # Check model names
            if not DEFAULT_MODEL:
                issues.append("DEFAULT_MODEL not set")
            else:
                config['default_model'] = DEFAULT_MODEL

            if not VISION_MODEL:
                issues.append("VISION_MODEL not set")
            else:
                config['vision_model'] = VISION_MODEL

            # Check TTS settings
            if not TTS_VOICE:
                issues.append("TTS_VOICE not set")
            else:
                config['tts_voice'] = TTS_VOICE

            config['tts_speed'] = TTS_SPEED
            config['ollama_host'] = OLLAMA_HOST

            return {
                'success': len(issues) == 0,
                'config': config,
                'issues': issues
            }

        self.run_test("Configuration Values", "Configuration", check_config)

    # ==================== LLM CLIENT TESTS ====================

    def test_llm_client(self):
        """Test LLM client initialization and basic chat."""
        print("\n" + "="*70)
        print("LLM CLIENT TESTS")
        print("="*70)

        def test_init():
            client = LLMClient()
            return {
                'success': True,
                'ollama_api_key_set': bool(client.ollama_api_key)
            }

        self.run_test("LLM Client Initialization", "LLM", test_init)

    def test_llm_simple_chat(self):
        """Test basic chat completion."""
        def test_chat():
            client = LLMClient()
            start = time.perf_counter()

            response = client.chat(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": "Say 'test successful' and nothing else"}],
                stream=False
            )

            latency = time.perf_counter() - start
            message = response.get('message', {}).get('content', '')

            return {
                'success': bool(message),
                'latency': round(latency, 3),
                'response_length': len(message),
                'response': message[:100]
            }

        self.run_test("Simple Chat Completion", "LLM", test_chat)

    def test_llm_streaming(self):
        """Test streaming chat completion."""
        def test_stream():
            client = LLMClient()
            start = time.perf_counter()

            response = client.chat(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": "Count from 1 to 5"}],
                stream=True
            )

            chunks = []
            first_chunk_time = None

            for chunk in response:
                if first_chunk_time is None:
                    first_chunk_time = time.perf_counter() - start
                content = chunk.get('message', {}).get('content', '')
                if content:
                    chunks.append(content)

            total_time = time.perf_counter() - start
            full_response = ''.join(chunks)

            return {
                'success': len(chunks) > 0,
                'ttft': round(first_chunk_time, 3) if first_chunk_time else 0,
                'total_time': round(total_time, 3),
                'chunks': len(chunks),
                'response': full_response[:100]
            }

        self.run_test("Streaming Chat", "LLM", test_stream)

    def test_llm_tool_calling(self):
        """Test tool calling functionality."""
        def test_tools():
            with open('tools.toml', 'r', encoding='utf-8') as f:
                tools_data = toml.load(f)
                tools = tools_data['tools']

            client = LLMClient()
            response = client.chat(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": "What's in my clipboard?"}],
                tools=tools,
                stream=False
            )

            message = response.get('message', {})
            has_tool_calls = 'tool_calls' in message

            return {
                'success': True,  # Just test it doesn't crash
                'tool_calls_present': has_tool_calls,
                'tool_calls': message.get('tool_calls', []) if has_tool_calls else []
            }

        self.run_test("Tool Calling", "LLM", test_tools)

    # ==================== AUDIO ENGINE TESTS ====================

    def test_audio_engine(self):
        """Test audio engine initialization."""
        print("\n" + "="*70)
        print("AUDIO ENGINE TESTS")
        print("="*70)

        def test_init():
            audio = AudioEngine()
            return {
                'success': True,
                'voice': audio.voice,
                'speed': audio.speed
            }

        result = self.run_test("Audio Engine Init", "Audio", test_init)

        if result.passed:
            # Only test TTS if engine initialized
            self.test_tts_generation()

    def test_tts_generation(self):
        """Test TTS audio generation (no playback)."""
        def test_tts():
            audio = AudioEngine()
            test_text = "Testing text to speech."

            start = time.perf_counter()
            audio_data = audio._generate_audio(test_text)
            duration = time.perf_counter() - start

            audio.shutdown()

            return {
                'success': audio_data is not None,
                'generation_time': round(duration, 3),
                'audio_samples': len(audio_data) if audio_data is not None else 0,
                'text_length': len(test_text)
            }

        self.run_test("TTS Generation", "Audio", test_tts)

    # ==================== SYSTEM TOOLS TESTS ====================

    def test_system_tools(self):
        """Test all system tools."""
        print("\n" + "="*70)
        print("SYSTEM TOOLS TESTS")
        print("="*70)

        # Test clipboard
        def test_clipboard_ops():
            # Set clipboard
            test_text = "ARIA test string"
            set_result = set_clipboard(test_text)

            if not set_result.get('success'):
                return {'success': False, 'error': 'Failed to set clipboard'}

            # Get clipboard
            time.sleep(0.1)  # Brief pause
            get_result = get_clipboard()

            if not get_result.get('success'):
                return {'success': False, 'error': 'Failed to get clipboard'}

            retrieved = get_result.get('content', '')
            matches = test_text in retrieved

            return {
                'success': matches,
                'set': test_text,
                'retrieved': retrieved[:50]
            }

        self.run_test("Clipboard Operations", "System Tools", test_clipboard_ops)

        # Test screenshot
        def test_screenshot_capture():
            result = take_screenshot()

            return {
                'success': result.get('success', False),
                'has_image': 'image_base64' in result,
                'width': result.get('width', 0),
                'height': result.get('height', 0)
            }

        self.run_test("Screenshot Capture", "System Tools", test_screenshot_capture)

        # Test active window
        def test_window():
            result = get_active_window()
            return {
                'success': result.get('success', False),
                'window_title': result.get('window_title', 'Unknown')[:50],
                'app_name': result.get('app_name', 'Unknown')
            }

        self.run_test("Active Window Detection", "System Tools", test_window)

    # ==================== SPOTIFY TOOLS TESTS ====================

    def test_spotify_tools(self):
        """Test Spotify integration."""
        print("\n" + "="*70)
        print("SPOTIFY TOOLS TESTS")
        print("="*70)

        # Test Spotify connection
        def test_spotify_connection():
            try:
                sp = get_spotify_client()
                # Try to get current playback (doesn't require active playback)
                current = sp.current_playback()
                return {
                    'success': True,
                    'connected': True,
                    'has_active_device': current is not None
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'warning': 'Spotify may not be authenticated or no active device'
                }

        self.run_test("Spotify Connection", "Spotify", test_spotify_connection)

        # Test current track (non-invasive)
        def test_current_track():
            result = spotify_current_track()
            return {
                'success': result.get('success', False),
                'track_name': result.get('track_name', 'N/A'),
                'is_playing': result.get('is_playing', False),
                'warning': result.get('error', None) if not result.get('success') else None
            }

        self.run_test("Get Current Track", "Spotify", test_current_track)

    # ==================== TOOL REGISTRY TESTS ====================

    def test_tool_registry(self):
        """Test tool registry and execution."""
        print("\n" + "="*70)
        print("TOOL REGISTRY TESTS")
        print("="*70)

        def test_registry():
            registered_tools = list(TOOL_HANDLERS.keys())
            return {
                'success': len(registered_tools) > 0,
                'tool_count': len(registered_tools),
                'tools': registered_tools
            }

        self.run_test("Tool Registry", "Tools", test_registry)

        # Test tool execution
        def test_execution():
            # Test a safe tool (clipboard get)
            result = execute_tool('get_clipboard', {})
            return {
                'success': isinstance(result, dict),
                'has_success_field': 'success' in result if isinstance(result, dict) else False
            }

        self.run_test("Tool Execution", "Tools", test_execution)

    # ==================== INTEGRATION TESTS ====================

    def test_integration(self):
        """Test end-to-end integration scenarios."""
        print("\n" + "="*70)
        print("INTEGRATION TESTS")
        print("="*70)

        def test_tool_with_llm():
            """Test LLM with tool calling and execution."""
            with open('tools.toml', 'r', encoding='utf-8') as f:
                tools_data = toml.load(f)
                tools = tools_data['tools']

            client = LLMClient()

            # Ask LLM to use a tool
            response = client.chat(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": "Get my clipboard content"}],
                tools=tools,
                stream=False
            )

            message = response.get('message', {})
            tool_calls = message.get('tool_calls', [])

            results = []
            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = tool_call['function']['name']
                    tool_args = tool_call['function']['arguments']
                    result = execute_tool(tool_name, tool_args)
                    results.append({
                        'tool': tool_name,
                        'success': result.get('success', False)
                    })

            return {
                'success': len(results) > 0 and all(r['success'] for r in results),
                'tool_calls_made': len(tool_calls),
                'executions': results
            }

        self.run_test("LLM + Tool Execution", "Integration", test_tool_with_llm)

    # ==================== MAIN TEST RUNNER ====================

    def run_all_tests(self):
        """Run complete test suite."""
        print("\n" + "="*70)
        print("ARIA COMPREHENSIVE TEST SUITE & BENCHMARK")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        self.start_time = time.perf_counter()

        # Run all test categories
        self.test_environment_variables()
        self.test_configuration_values()
        self.test_llm_client()
        self.test_llm_simple_chat()
        self.test_llm_streaming()
        self.test_llm_tool_calling()
        self.test_audio_engine()
        self.test_system_tools()
        self.test_spotify_tools()
        self.test_tool_registry()
        self.test_integration()

        self.end_time = time.perf_counter()

        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate detailed test report."""
        total_duration = self.end_time - self.start_time

        # Calculate statistics
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total_tests - passed
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0

        # Group by category
        categories = {}
        for result in self.results:
            cat = result.category
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0, 'duration': 0}

            if result.passed:
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1
            categories[cat]['duration'] += result.duration

        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print(f"Total Duration: {total_duration:.2f}s")

        # Category breakdown
        print("\n" + "-"*70)
        print("CATEGORY BREAKDOWN")
        print("-"*70)
        for cat, stats in categories.items():
            total = stats['passed'] + stats['failed']
            rate = (stats['passed'] / total * 100) if total > 0 else 0
            print(f"\n{cat}:")
            print(f"  Tests: {total} | Passed: {stats['passed']} | Failed: {stats['failed']}")
            print(f"  Pass Rate: {rate:.1f}% | Duration: {stats['duration']:.2f}s")

        # Detailed results
        print("\n" + "-"*70)
        print("DETAILED RESULTS")
        print("-"*70)

        for result in self.results:
            status = "✓ PASS" if result.passed else "✗ FAIL"
            print(f"\n[{status}] {result.category} > {result.name}")
            print(f"  Duration: {result.duration:.3f}s")

            if result.error:
                print(f"  Error: {result.error}")

            if result.warnings:
                for warning in result.warnings:
                    print(f"  Warning: {warning}")

            if result.details:
                for key, value in result.details.items():
                    if key not in ['success', 'error', 'warning']:
                        # Convert non-serializable objects to string
                        try:
                            if isinstance(value, (list, dict)):
                                print(f"  {key}: {json.dumps(value, indent=4)}")
                            else:
                                print(f"  {key}: {value}")
                        except (TypeError, ValueError):
                            print(f"  {key}: {str(value)}")

        # Performance metrics
        print("\n" + "-"*70)
        print("PERFORMANCE METRICS")
        print("-"*70)

        # LLM performance
        llm_tests = [r for r in self.results if r.category == "LLM" and r.passed]
        if llm_tests:
            print("\nLLM Performance:")
            for test in llm_tests:
                if 'latency' in test.details:
                    print(f"  {test.name}: {test.details['latency']}s")
                if 'ttft' in test.details:
                    print(f"  {test.name} TTFT: {test.details['ttft']}s")

        # Audio performance
        audio_tests = [r for r in self.results if r.category == "Audio" and r.passed]
        if audio_tests:
            print("\nAudio Performance:")
            for test in audio_tests:
                if 'generation_time' in test.details:
                    print(f"  TTS Generation: {test.details['generation_time']}s")

        # System tools performance
        system_tests = [r for r in self.results if r.category == "System Tools" and r.passed]
        if system_tests:
            print("\nSystem Tools Performance:")
            avg_duration = sum(t.duration for t in system_tests) / len(system_tests)
            print(f"  Average Tool Execution: {avg_duration:.3f}s")

        # Save JSON report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total_tests,
                'passed': passed,
                'failed': failed,
                'pass_rate': round(pass_rate, 2),
                'total_duration': round(total_duration, 2)
            },
            'categories': categories,
            'results': [r.to_dict() for r in self.results]
        }

        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n{'='*70}")
        print(f"📊 Detailed report saved to: {filename}")
        print(f"{'='*70}\n")


def main():
    """Run the test suite."""
    try:
        suite = ARIATestSuite()
        suite.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
