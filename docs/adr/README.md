# Architecture Decision Records (ADRs)

This directory captures *durable technical decisions* for Trackit. ADRs prevent silent drift by making
decisions explicit, reviewable, and versioned.

## How to use ADRs in this repo

- **Do not** load all ADRs by default. Read this index first.
- When planning or implementing changes, load only ADRs that govern the areas you touch.
- If a change conflicts with an accepted ADR, create a new ADR that **supersedes** the old one.

## ADR format

Each ADR should include:
- Status (Proposed / Accepted / Superseded)
- Context (why the decision is needed)
- Decision (the rules/invariants we commit to)
- Consequences (tradeoffs, impacts)
- Alternatives (what we did not choose)

## ADR index

- **ADR-0001: Layer boundaries and dependency direction**
  - Governs: overall architecture, imports, layering, ORM/domain separation.
  - Read when touching: `src/trackit/cli/`, `src/trackit/domain/`, `src/trackit/database/`, `migrations/`.

- **ADR-0002: User-visible filtering semantics**
  - Governs: date-range flags and category filtering semantics that users rely on.
  - Read when touching: `src/trackit/utils/date_parser.py`, CLI commands that accept date options,
    summary/list behaviors, category traversal.

## Notes

- Playbooks under `docs/playbooks/` contain detailed procedures and examples.
- ADRs are the source of truth for *what must not drift*.
