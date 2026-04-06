@echo off
REM ARIA Test Suite Runner
REM Installs dependencies if needed and runs comprehensive tests

echo ============================================================
echo ARIA Comprehensive Test Suite
echo ============================================================
echo.

REM Check if python-dotenv is installed
python -c "import dotenv" 2>nul
if errorlevel 1 (
    echo [1/2] Installing missing dependencies...
    pip install python-dotenv -q
    echo      Done!
    echo.
)

echo [2/2] Running test suite...
echo.

REM Run the test suite
python test_suite.py

echo.
echo ============================================================
echo Test complete! Check test_report_*.json for details
echo ============================================================
pause
