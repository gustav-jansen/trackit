# ADR-0003: Domain error taxonomy

**Status:** Proposed  
**Date:** 2026-02-02

## Context

Domain services currently raise `ValueError` with string messages and sometimes return `None`
or empty collections for failure cases. This makes error intent ambiguous, mixes validation
failures with not-found scenarios, and forces CLI code to infer meaning from strings.

We need a stable, explicit contract for domain errors that preserves existing CLI behavior
while enabling consistent handling across services and future improvements (logging,
telemetry, retries, and user guidance).

## Decision

1) **Typed domain errors:**
   - Introduce a domain error hierarchy rooted at `DomainError`, a subclass of `ValueError`.
   - Use subclasses to convey category:
     - `ValidationError` for invalid inputs or failed validation.
     - `NotFoundError` when an expected entity/path is missing.
     - `ConflictError` for uniqueness or duplicate conflicts.
     - `DependencyError` when an operation is blocked by dependent data.

2) **Message contract:**
   - Error messages remain human-readable and stable so CLI output can stay unchanged.
   - The message remains the primary user-facing text; categories drive programmatic handling.

3) **Layering:**
   - Domain services raise these errors; CLI maps them to existing messages and exit codes.
   - Database layer returns `None` for not-found where appropriate; domain maps to `NotFoundError`.

## Consequences

- Clarifies error intent without changing user-visible behavior.
- Enables uniform error handling across list/summary/import flows.
- Requires incremental migration of domain services to raise typed errors.

## Alternatives considered

- Continue using `ValueError` strings only (rejected: ambiguous and hard to extend).
- Return result objects instead of exceptions (deferred: larger behavior change).
