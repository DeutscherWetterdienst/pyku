---
name: testing
description: Test execution with pytest in the active Python environment.
---

# Testing Skill

## Running Tests

The canonical test command uses pytest for clean, concise output:

```bash
pytest testing/ -v --tb=short
```

**Important:** Use the active Python environment provided by the host and
OpenCode setup. Do not reset or replace it before running tests.

This collects all test files matching `*_test.py` in the `testing/` directory.

## Why pytest?

- Clean progress indicators with dots
- ✓ markers for passed tests
- Concise summary (e.g., `46 passed, 7 warnings, 45 subtests passed`)
- Short tracebacks for easy debugging

## Other Useful pytest Commands

- `pytest testing/ -q` — Quiet mode (dots only)
- `pytest testing/ -k "pattern"` — Run tests matching pattern
- `pytest testing/ --durations=10` — Show slowest 10 tests

## Testing Modified Functions

When testing functions that have been updated or refactored:

1. **Docstring Execution:** Test the function directly by executing the `ipython`
   code snippet embedded in its docstring.

2. **Failure Handling:** If an error occurs during execution:
   1. Immediately stop execution.
   2. Pause and present the error and current state for human review before
      attempting any further changes or re-testing.
