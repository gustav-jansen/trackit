# Playbook: Category filtering semantics

Governing ADRs: ADR-0002

## When to read
Read this before changing category filtering behavior, summary logic, or category tree traversal.

## Current semantics (must not drift accidentally)
- Summary uses descendant categories (via `_get_all_descendant_ids()` or equivalent).
- Transaction list filters by exact category only.

## If you want to change semantics
- Treat as a user-visible behavior change.
- Update README + tests.
- Consider an ADR (decision record) if it impacts multiple commands/services.

## Testing checklist
- [ ] Summary includes descendants
- [ ] Transaction list does not include descendants unless explicitly requested
