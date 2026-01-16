# ADR-0001: Layer boundaries and dependency direction

**Status:** Accepted  
**Date:** 2026-01-16

## Context

Trackit is a CLI-centric application with domain logic and a database implementation.
Without explicit boundaries, code tends to drift toward:
- domain logic depending on ORM/query details,
- CLI concerns leaking into services,
- tests becoming brittle and expensive.

We want a structure that keeps domain logic testable and stable, while allowing the DB layer
to evolve independently.

## Decision

We adopt a strict dependency direction and boundary rules:

1. **Layering (dependency direction):**
   - CLI → Domain → Database
   - Dependencies must only flow “down” this list.

2. **Domain layer constraints (`src/trackit/domain/`):**
   - Must not import SQLAlchemy or database implementation modules.
   - Must not depend on Click (CLI) types/exceptions.
   - Uses domain entities and domain-centric interfaces only.

3. **Database layer constraints (`src/trackit/database/` + `migrations/`):**
   - All persistence is accessed through the `Database` interface (`src/trackit/database/base.py`).
   - SQLAlchemy ORM models must not be returned outside the database layer.
   - ORM ↔ domain conversion happens in mapper functions (e.g., `src/trackit/database/mappers.py`).

4. **CLI layer constraints (`src/trackit/cli/`):**
   - CLI parses user input, calls domain services, renders output.
   - CLI owns user interaction and exit codes; domain/services use Python exceptions for invalid input.

5. **Testing expectations:**
   - Prefer unit tests at the domain/service level.
   - DB behavior should be tested through domain/service boundaries where possible.
   - CLI tests are for parsing/dispatch and user-visible behavior, not business logic.

## Consequences

- Domain logic remains testable without a database.
- Database refactors are isolated to the DB layer + mappers.
- Some “convenient” shortcuts (domain doing queries directly) are intentionally disallowed.

## Alternatives considered

- Let domain call ORM directly (rejected: tightly couples business logic to persistence details).
- Put all logic in CLI commands (rejected: makes testing and reuse difficult).
