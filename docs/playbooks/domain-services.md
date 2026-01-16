# Playbook: Domain services

Governing ADRs: ADR-0001

## When to read
Read this before adding/modifying code under `src/trackit/domain/` or changing domain entities.

## Principles
- Services depend on the `Database` interface, not SQLAlchemy specifics.
- Inputs/outputs should be domain entities (immutable dataclasses from `entities.py`).
- Raise `ValueError` for invalid operations.

## Adding or changing a service
- [ ] Define/extend a service method with clear parameters and return types
- [ ] Validate inputs early (raise `ValueError` with actionable messages)
- [ ] Call only `Database` interface methods (no ORM access)
- [ ] Return domain entities, not ORM objects

## Dates and money
- Use `date`, not `datetime`, in domain logic.
- Use `Decimal` for monetary values.
- Parse user-facing amounts with `trackit.utils.amount_parser.parse_amount`.
