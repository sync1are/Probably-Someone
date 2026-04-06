# ARIA Test Suite

Comprehensive functionality and benchmark testing for ARIA voice assistant.

## Quick Start

```bash
python test_suite.py
```

## What It Tests

### 1. Configuration (2 tests)
- ✓ Environment variables (API keys, credentials)
- ✓ Configuration values (models, TTS settings)

### 2. LLM Client (4 tests)
- ✓ Client initialization
- ✓ Simple chat completion (latency measured)
- ✓ Streaming responses (TTFT measured)
- ✓ Tool calling functionality

### 3. Audio Engine (2 tests)
- ✓ Engine initialization
- ✓ TTS generation performance

### 4. System Tools (3 tests)
- ✓ Clipboard operations (set/get)
- ✓ Screenshot capture
- ✓ Active window detection

### 5. Spotify Integration (2 tests)
- ✓ API connection
- ✓ Current track info

### 6. Tool Registry (2 tests)
- ✓ Tool registration
- ✓ Tool execution

### 7. Integration (1 test)
- ✓ End-to-end: LLM → Tool Call → Execution

## Output

### Console Output
- Real-time test progress with ✓/✗ indicators
- Duration for each test
- Category summaries
- Detailed results with metrics
- Performance breakdown

### JSON Report
Saved as `test_report_YYYYMMDD_HHMMSS.json`:
```json
{
  "timestamp": "2026-04-06T18:30:00",
  "summary": {
    "total_tests": 16,
    "passed": 14,
    "failed": 2,
    "pass_rate": 87.5,
    "total_duration": 12.45
  },
  "categories": {...},
  "results": [...]
}
```

## Performance Metrics

The suite measures:
- **LLM Latency**: Response time for chat completions
- **TTFT**: Time to first token (streaming)
- **TTS Generation**: Audio generation speed
- **Tool Execution**: Individual tool performance
- **Total Duration**: Complete test suite runtime

## Expected Results

On a healthy system:
- **Pass Rate**: 90-100%
- **LLM Latency**: 0.5-3s (depends on model)
- **TTFT**: 0.1-1s
- **TTS Generation**: 0.1-0.5s
- **Tool Execution**: <0.1s each

## Common Issues

### Spotify Tests Fail
- **Cause**: Not authenticated or no active Spotify device
- **Fix**: Open Spotify app and play something, then re-auth

### LLM Tests Fail
- **Cause**: Ollama not running or wrong API key
- **Fix**: Check `OLLAMA_API_KEY` in `.env` and Ollama service

### Screenshot Fails
- **Cause**: Display/graphics driver issues
- **Fix**: Check PIL/Pillow installation

## Integration with CI/CD

Add to your workflow:
```bash
python test_suite.py && echo "Tests passed" || echo "Tests failed"
```

Exit codes:
- `0`: All tests passed
- `1`: Some tests failed (see report)
