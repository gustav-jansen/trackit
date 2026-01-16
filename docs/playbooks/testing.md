# Playbook: Tests and validation

## When to read
Read this before implementing a new feature or changing behavior.

## Required checks
- Run: `uv run pytest tests/`
- Add tests for every new feature or behavior change
- Update `README.md` for CLI changes

## Test strategy
Prefer testing:
1) Domain services (highest value, stable)
2) Database implementations (integration-ish)
3) CLI parsing/dispatch (only where needed)

## Good tests usually include
- Typical case
- Boundary case
- Bad input -> error handling path
