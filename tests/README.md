# Testing Guide for JARVIS Voice Agent

Quick reference for running tests on the JARVIS project.

**See also:** `/docs_imported/agents/testing.md` for comprehensive testing patterns and quality guidelines.

## Quick Start

### Installation

```bash
# Install test dependencies (already in requirements.txt, but to be explicit)
pip install pytest pytest-asyncio pytest-mock pytest-cov pytest-timeout
```

### Run All Tests

```bash
# Run all tests with verbose output
pytest

# Run with coverage report
pytest --cov=tools --cov-report=html
# Opens coverage report at: htmlcov/index.html
```

### Run Specific Tests

```bash
# Run a single test file
pytest tests/test_weather.py

# Run a specific test
pytest tests/test_weather.py::TestWeatherTool::test_get_weather_valid_location

# Run tests matching a pattern
pytest -k "weather"  # All tests with "weather" in name
pytest -k "error"    # All tests with "error" in name
```

### Run by Category

```bash
# Run only unit tests (fast)
pytest -m "unit"

# Run only integration tests
pytest -m "integration"

# Skip slow tests (network/API)
pytest -m "not slow"

# Run only async tests
pytest tests/test_weather.py -v
```

## Test Structure

```
tests/
├── __init__.py           # Test package marker
├── conftest.py           # Shared fixtures and configuration
├── test_weather.py       # Weather tool tests
├── test_search.py        # Search tool tests
├── test_email.py         # Email tool tests
├── test_agent.py         # Agent integration tests (create as needed)
└── logs/                 # Test output logs
```

## Testing Tools

### Fixtures (in `conftest.py`)

**`mock_context`** — Mock RunContext for tool testing
```python
@pytest.mark.asyncio
async def test_my_tool(mock_context):
    result = await my_tool(mock_context, "test_input")
    assert isinstance(result, str)
```

**`mock_job_context`** — Mock JobContext for integration tests
```python
@pytest.mark.asyncio
async def test_agent_session(mock_job_context):
    # test code here
    pass
```

### Markers

```bash
# Slow tests (requires network)
@pytest.mark.slow
async def test_weather_real_api():
    pass

# Mark as integration test
@pytest.mark.integration
async def test_agent_with_apis():
    pass

# Mark as e2e
@pytest.mark.e2e
async def test_full_conversation():
    pass
```

## Common Test Patterns

### Testing a Tool (Unit Test)

```python
import pytest
from tools.my_tool import my_tool

@pytest.mark.asyncio
async def test_my_tool_happy_path(mock_context):
    """Test: Tool succeeds with valid input."""
    result = await my_tool(mock_context, "valid_input")
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_my_tool_error(mock_context):
    """Test: Tool handles errors gracefully."""
    result = await my_tool(mock_context, "invalid_input")
    assert "error" in result.lower() or result == ""
```

### Mocking External API

```python
from unittest.mock import patch

@pytest.mark.asyncio
async def test_my_tool_with_mock_api(mock_context):
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"status": "ok"}
        
        result = await my_tool(mock_context, "test")
        assert isinstance(result, str)
```

### Mocking Errors

```python
@pytest.mark.asyncio
async def test_tool_timeout(mock_context):
    with patch('requests.get', side_effect=TimeoutError("API timeout")):
        result = await my_tool(mock_context, "test")
        assert "error" in result.lower()
```

## Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=tools --cov-report=html

# View report (opens in browser on Windows)
start htmlcov/index.html

# Generate terminal report
pytest --cov=tools --cov-report=term-missing

# Only report on specific files
pytest --cov=tools --cov-report=term-missing tests/test_weather.py
```

**Coverage Goals:**
- Unit tests: 70%+ coverage
- Tools: 80%+ coverage (critical for production)
- Happy path: 100%
- Edge cases & errors: 50%+

## Debugging Failed Tests

### See Full Traceback

```bash
# Show full error details
pytest --tb=long

# Show local variables in traceback
pytest -vv --tb=short
```

### Print Debug Output

```python
@pytest.mark.asyncio
async def test_my_tool(mock_context):
    result = await my_tool(mock_context, "test")
    print(f"Result: {result}")  # Shows in test output
    assert isinstance(result, str)
```

Run with `-s` to see print statements:
```bash
pytest tests/test_weather.py -s
```

### Run Test with Breakpoint

```python
@pytest.mark.asyncio
async def test_my_tool(mock_context):
    breakpoint()  # Stops here; use `c` to continue
    result = await my_tool(mock_context, "test")
```

Run with `-n` to disable output capture:
```bash
pytest tests/test_weather.py --pdb
```

### Only Run Failing Tests

```bash
# Run last failed tests
pytest --lf

# Run failed + passing tests
pytest --ff
```

## Continuous Integration

### GitHub Actions Example

Add to `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-mock pytest-cov
      
      - name: Run tests
        run: pytest --cov=tools --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
```

## Pre-Commit Hook (Optional)

Run tests automatically before committing:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest --cov=tools
        language: system
        types: [python]
        stages: [commit]
        pass_filenames: false
EOF

# Install hook
pre-commit install
```

## Writing New Tests

### Checklist for New Tool Tests

- [ ] Create `tests/test_<tool_name>.py`
- [ ] Add `TestCase` class(es) for organization
- [ ] Test happy path (valid input)
- [ ] Test error cases (invalid input, API errors, timeout)
- [ ] Test edge cases (empty, very long, special chars, unicode)
- [ ] Use `@pytest.mark.asyncio` for async tests
- [ ] Use `mock_context` fixture
- [ ] Add docstrings to each test
- [ ] Mock external API calls
- [ ] Run tests: `pytest tests/test_<tool_name>.py -v`
- [ ] Check coverage: `pytest tests/test_<tool_name>.py --cov=tools`

### Template for New Tool Test File

```python
"""Unit tests for the <tool_name> tool."""
import pytest
from unittest.mock import AsyncMock, patch

from tools.<tool_name> import <tool_function>


class Test<ToolName>:
    """Test suite for <tool_name> tool."""

    @pytest.mark.asyncio
    async def test_<tool_name>_happy_path(self, mock_context):
        """Test: Tool succeeds with valid input."""
        result = await <tool_function>(mock_context, "valid_input")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_<tool_name>_error_handling(self, mock_context):
        """Test: Tool handles errors gracefully."""
        result = await <tool_function>(mock_context, "invalid_input")
        assert isinstance(result, str)
        # Should not crash
```

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'tools'`
**Solution:** Run pytest from project root: `cd /path/to/jarvis && pytest`

### Issue: Async test times out
**Solution:** Increase timeout or add timeout decorator:
```python
@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_my_tool():
    pass
```

### Issue: Mock not working
**Solution:** Use context manager instead of decorator:
```python
# Wrong
@patch('module.function')
async def test_foo(mock_fn):
    pass

# Correct
@pytest.mark.asyncio
async def test_foo():
    with patch('module.function') as mock_fn:
        pass
```

### Issue: Tests pass locally but fail in CI
**Solution:** Check for:
- Missing environment variables
- Hardcoded paths (use relative paths)
- Time-dependent tests (use freezegun)
- Network-dependent tests (mock APIs)

## Resources

- **pytest documentation:** https://docs.pytest.org
- **pytest-asyncio:** https://github.com/pytest-dev/pytest-asyncio
- **unittest.mock:** https://docs.python.org/3/library/unittest.mock.html
- **Testing in LiveKit Agents:** `/docs_imported/agents/testing.md`

## Next Steps

1. Run `pytest` to verify tests pass
2. Run `pytest --cov` to check coverage
3. Add more tests as you add tools
4. Integrate tests into CI/CD pipeline
5. Monitor tool quality with metrics

---

**Have questions?** Check `/docs_imported/agents/testing.md` or your tool's docstring.
