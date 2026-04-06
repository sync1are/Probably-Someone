# ARIA Testing Guide

## Quick Start

### Option 1: Windows Batch Script (Easiest)
```bash
run_tests.bat
```
This will auto-install dependencies and run tests.

### Option 2: Manual
```bash
# Install dependencies (if needed)
pip install python-dotenv

# Run tests
python test_suite.py
```

---

## What Gets Tested

### ✅ Configuration Layer
- Environment variables (API keys)
- Config values (models, TTS settings)

### ✅ LLM Client
- Initialization
- **Chat completion latency** (measured)
- **Streaming TTFT** (measured)
- Tool calling support

### ✅ Audio Engine
- TTS initialization
- **Audio generation speed** (measured)

### ✅ System Tools
- Clipboard read/write
- Screenshot capture  
- Active window detection

### ✅ Spotify Integration
- API authentication
- Current track info
- *(Note: Playback tests are non-invasive)*

### ✅ Tool Registry
- Tool registration count
- Tool execution pipeline

### ✅ End-to-End Integration
- LLM → Tool Call → Execution flow

---

## Test Reports

### Console Output
Real-time progress with:
- ✓/✗ status for each test
- Execution time per test
- Category summaries
- Performance metrics

### JSON Report
`test_report_YYYYMMDD_HHMMSS.json` contains:
```json
{
  "summary": {
    "total_tests": 16,
    "passed": 14,
    "pass_rate": 87.5,
    "total_duration": 12.34
  },
  "results": [
    {
      "name": "Simple Chat Completion",
      "passed": true,
      "duration": 1.234,
      "details": {
        "latency": 1.234,
        "response_length": 45
      }
    }
  ]
}
```

---

## Performance Benchmarks

Expected metrics on healthy system:

| Metric | Target | Category |
|--------|--------|----------|
| LLM Latency | 0.5-3s | Depends on model size |
| Streaming TTFT | 0.1-1s | Critical for voice |
| TTS Generation | 0.1-0.5s | Per sentence |
| Tool Execution | <0.1s | System tools |
| Total Test Duration | ~10-20s | Full suite |

---

## Troubleshooting

### ❌ "ModuleNotFoundError: dotenv"
**Fix:** Run `pip install python-dotenv` or use `run_tests.bat`

### ❌ Spotify tests fail
**Cause:** Not authenticated or no active device
**Fix:** 
1. Open Spotify app
2. Play any song
3. Re-run tests

### ❌ LLM tests timeout/fail
**Cause:** Ollama not running or wrong API key
**Fix:**
1. Check Ollama service is running
2. Verify `OLLAMA_API_KEY` in `.env`
3. Test with: `curl http://localhost:11434`

### ❌ Screenshot fails
**Cause:** PIL/graphics driver issues  
**Fix:** Reinstall Pillow: `pip install --upgrade Pillow`

---

## CI/CD Integration

```bash
# Run tests and check exit code
python test_suite.py
if [ $? -eq 0 ]; then
    echo "✅ All tests passed"
else
    echo "❌ Tests failed - check report"
    exit 1
fi
```

---

## Comparing Performance

Run tests before and after changes:

```bash
# Before changes
python test_suite.py
# → Saves test_report_20260406_120000.json

# Make your changes...

# After changes  
python test_suite.py
# → Saves test_report_20260406_123000.json

# Compare the two JSON files
```

Look for:
- ⬇️ Reduced latency (good!)
- ⬆️ Increased pass rate (good!)
- 🐛 New failures (investigate!)

---

## Test Files

- `test_suite.py` - Main comprehensive test suite
- `test_nvidia.py` - NVIDIA API latency benchmark
- `run_tests.bat` - Windows launcher script
- `test_report_*.json` - Generated reports
