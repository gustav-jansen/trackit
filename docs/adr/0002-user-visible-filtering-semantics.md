# ADR-0002: User-visible filtering semantics

**Status:** Accepted  
**Date:** 2026-01-16

## Context

Trackit provides user-visible filtering behaviors (date ranges, category filtering) that form part of
the CLI’s “contract.” Over time, these behaviors can drift unintentionally during refactors unless
we define them explicitly.

This ADR captures the semantics that must not change without deliberate decision-making,
tests, and documentation updates.

## Decision

### 1) Date range selection

1. **Single source of truth:**
   - Date parsing and range computation must be centralized in `trackit.utils.date_parser` helpers.

2. **Mutual exclusivity:**
   - “Period” flags (e.g., this-month/last-month style flags) are mutually exclusive.
   - Period flags must not be combined with explicit start/end date arguments.

3. **Validation behavior:**
   - Invalid combinations must fail fast and produce a clear error message.
   - CLI-level errors exit non-zero; services raise `ValueError`.

4. **Boundary expectations:**
   - Date ranges represent *calendar dates* (use `date`, not `datetime`) in domain logic.

### 2) Category filtering semantics

1. **Transaction list filtering:**
   - Transaction listing filters by **exact category** by default (no implicit descendant expansion).

2. **Summary filtering:**
   - Summaries may include descendant categories (category tree expansion) where the UI/UX indicates
     “include subcategories” behavior.

3. **No silent behavior change:**
   - Any change to list-vs-summary semantics requires:
     - updated tests covering the changed behavior, and
     - an update to `README.md` (user-facing docs),
     - and if the change is broad, a new ADR that supersedes this one.

## Consequences

- Refactors must preserve these behaviors unless explicitly changed.
- Tests should encode these semantics to prevent regressions.

## Alternatives considered

- Always include descendants for both list and summary (rejected: changes user expectations and can broaden results unexpectedly).
- Never include descendants anywhere (rejected: makes summaries less useful for hierarchical categories).
