# Playbook: Database layer

Governing ADRs: ADR-0001

## When to read
Read this before changing anything in `src/trackit/database/` or anything related to migrations.

## Layering rules
- Database access must go through the `Database` interface (`src/trackit/database/base.py`).
- SQLAlchemy models must not leak outside the database layer.
- Convert ORM <-> domain using `src/trackit/database/mappers.py`.

## Adding a new DB capability
1) Add a method to the `Database` interface
   - Keep it domain-centric (domain types in/out)
2) Implement it in `sqlalchemy_db.py`
3) Add/update mapper functions as needed
4) Add tests that exercise the behavior through the service layer (preferred)

## Error / not-found policy
- Database layer returns `None` for not-found where appropriate (match existing patterns).
- Do not raise Click exceptions from the DB layer.

## SQLAlchemy usage notes
- Prefer explicit session lifecycle and transactions consistent with existing code.
- Avoid performing complex business logic in ORM query code.
