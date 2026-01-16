# Playbook: Date filters and ranges

Governing ADRs: ADR-0002

## When to read
Read this before modifying:
- `src/trackit/utils/date_parser.py`
- Any CLI/service code that accepts date ranges or period flags

## Canonical helpers
- Use `parse_date()` for relative strings
- Use `get_date_range()` for period flags

## Rules / invariants
- Period flags are mutually exclusive (only one period at a time).
- Period flags cannot combine with explicit start/end dates.

## Expected behavior (examples)
- "this-month" → range spanning first..last day of current month
- explicit `--start`/`--end` → inclusive range (confirm existing behavior in code/tests)
- invalid combinations → fail early (CLI: stderr + exit 1; services: `ValueError`)

## Testing checklist
- [ ] Each period flag maps to the correct start/end
- [ ] Mutually exclusive flags are enforced
- [ ] Combining period + start/end is rejected
- [ ] Edge cases: month boundaries, leap day, year boundaries
