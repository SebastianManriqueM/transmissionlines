---
name: pytest-testing
description: "Write, review, and run function-based pytest tests with pytest-cov and pytest-benchmark. Use when adding tests, fixing test failures, measuring Python performance, or checking coverage."
argument-hint: "Describe the behavior, target module, expected outcome, and any coverage or benchmark requirement"
user-invocable: true
---

# Pytest Testing

## Outcome

Deliver focused, deterministic, function-based pytest coverage that verifies the
public behavior of Python code. Measure performance only where it matters and
collect actionable coverage.

## When to Use

- Adding, repairing, reviewing, or running Python tests.
- Implementing or changing a Python feature, bug fix, refactor, or public API.
- Diagnosing a regression, coverage gap, or performance change.
- Adding benchmarks with `pytest-benchmark`.

## Non-Negotiable Test Style

- Use standalone `test_*` functions only.
- Do not define test classes.
- Do not use `unittest.TestCase`, custom assertion frameworks, or test methods.
- Use plain `assert` statements and `pytest.raises`.
- Follow the nearest test module's imports, naming, fixtures, data paths, and
  assertion style.

## Discover the Local Test Contract

Before changing tests or code:

1. Read `pyproject.toml`, `pytest.ini`, `setup.cfg`, `tox.ini`, and dependency
   files when present to identify the configured Python environment, test paths,
   markers, coverage settings, and benchmark options.
2. Locate the nearest relevant `test_*.py` function and the public API that owns
   the behavior.
3. Use the repository's established runner. If no runner is configured, prefer
   `python -m pytest` in the selected project environment and state that
   assumption.
4. Confirm whether `pytest-cov` and `pytest-benchmark` are installed before
   requiring their commands. Do not add dependencies unless the user requests
   dependency changes.

## Procedure

### 1. Define the Behavioral Contract

1. State the expected normal behavior, a meaningful boundary or invalid case,
   and the expected failure mode before implementation.
2. Prefer public APIs and observable outputs over private implementation
   details.
3. Write one small failing `test_<behavior>_<condition>_<outcome>` function per
   behavior slice before changing production code.
4. Use `pytest.mark.parametrize` for the same behavior across independent,
   readable cases. Add `id=` values when they make failures clearer.

### 2. Build Deterministic Test Inputs

1. Reuse small, documented repository fixtures and data files when they isolate
   the required behavior.
2. Use `tmp_path` for filesystem behavior and `monkeypatch` for environment or
   dependency seams.
3. Keep fixtures narrowly scoped and function-scoped by default. Use fixtures
   only for genuine shared setup or cleanup.
4. Avoid network calls, wall-clock time, uncontrolled randomness, machine-local
   absolute paths, mutable globals, and test-order dependencies. Control or
   inject these dependencies when their behavior must be tested.

### 3. Assert the Contract

1. Assert results, externally visible state, and error messages that are part
   of the public contract.
2. Use `pytest.raises(ExpectedException, match="...")` for invalid inputs and
   documented failures.
3. Compare floating-point values with
   `pytest.approx(expected, abs=tolerance)` or an explicitly justified relative
   tolerance.
4. Keep assertions precise enough to detect regressions without coupling tests
   to incidental internal representation.

### 4. Measure Coverage

1. Run the new test first, then its nearest module, then the relevant suite.
2. When `pytest-cov` is available, collect terminal and missing-line coverage:

```powershell
python -m pytest test/test_target.py -v --cov=src --cov-report=term-missing
```

3. Replace `test/` and `src` with the repository's configured paths. Respect
   existing coverage thresholds and omit generated, vendored, or intentionally
   untestable code only through existing project configuration.
4. Use uncovered lines to add behavior-focused cases; do not write tests merely
   to increase the percentage.

### 5. Benchmark Responsibly

1. Add a benchmark only for a performance-sensitive, stable public operation.
2. Benchmark a representative workload with fixed inputs and no network, file
   system setup, or unrelated work in the timed callable.
3. Use the `benchmark` fixture in a standalone test function:

```python
def test_parse_records_benchmark(benchmark, sample_records):
    result = benchmark(parse_records, sample_records)

    assert result
```

4. Run focused benchmarks with `python -m pytest test/test_target.py --benchmark-only`.
5. Compare benchmark results only under comparable hardware, Python versions,
   dependency versions, and inputs. Do not make brittle time-limit assertions
   in ordinary tests.

### 6. Validate and Report

1. Run the focused test, then nearby tests, before widening scope.
2. Rerun the selected tests to check determinism when the behavior has external
   inputs or performance-sensitive code.
3. Run coverage and benchmarks only when relevant and available.
4. Report commands run, test results, coverage findings, benchmark comparison
   context, and any unavailable tools.

## Commands

Use configured project commands in preference to these generic examples:

```powershell
python -m pytest test/test_target.py -v
python -m pytest test/test_target.py -k behavior_name -v
python -m pytest test -v
python -m pytest test --cov=src --cov-report=term-missing
python -m pytest test/test_target.py --benchmark-only
```

## Anti-Patterns

- Test classes, `unittest.TestCase`, custom assertion frameworks, or test methods.
- Tests that only assert an object is not `None`.
- Exact equality for unstable floating-point results or overly broad tolerances.
- A broad end-to-end test that hides independent failures instead of focused
  behavioral tests.
- Hard-coded local paths, `print`-driven validation, network access, or hidden
  dependency on a locally installed executable.
- Timed assertions that fail due to normal machine variation.
- Treating coverage percentage as a substitute for meaningful assertions.

## Completion Criteria

- Every added test is a standalone `test_*` function; no test classes exist.
- Coverage includes the normal behavior and an appropriate boundary or error
  case for the changed behavior.
- Tests are deterministic and use public behavior-focused assertions.
- Relevant focused pytest commands pass.
- Coverage and benchmark checks are run when applicable and available, or their
   absence is reported clearly.