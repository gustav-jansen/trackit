# AGENTS.md

Global, always-on rules for agentic coding assistants working in the Trackit repository.

This file is intentionally **lean**. Detailed, topic-specific rules live in playbooks
under `docs/playbooks/` and must be loaded explicitly when relevant.

---

## Project Summary

Trackit is a Python CLI for expense tracking with a layered architecture:

- CLI layer: `src/trackit/cli/`
- Domain layer: `src/trackit/domain/`
- Database layer: `src/trackit/database/`
- Migrations: `migrations/`
- Tests: `tests/`

---

## How to Work in This Repo

Before planning or implementing changes:

1. Identify which areas of the codebase will be touched.
2. Load and follow the corresponding playbook(s) from `docs/playbooks/`.
3. Do **not** silently change user-visible semantics or architectural boundaries.
   - Update tests and documentation as required.
   - If the change affects multiple areas or future design, add or update an ADR
     under `docs/adr/`.

Agents should prefer small, reviewable changes and follow existing patterns.

Read docs/adr/README.md first, then load only the ADRs relevant to the areas you touch.

---

## Playbooks (Load on Demand)

- CLI commands and UX: `docs/playbooks/cli.md`
- Domain services and entities: `docs/playbooks/domain-services.md`
- Database access and migrations: `docs/playbooks/database.md`
- Date parsing and period filters: `docs/playbooks/date-filters.md`
- Category filtering semantics: `docs/playbooks/category-filtering.md`
- Testing strategy and expectations: `docs/playbooks/testing.md`

---

## Build and Test

### Environment
- Python 3.12+
- Package manager: `uv`

### Install
```bash
uv sync
```

### Run CLI
```bash
trackit --help
```

### Tests
```bash
uv run pytest tests/
```

---

## Non-Negotiables

- Tests are required for new or changed behavior.
- Documentation must be updated for user-visible changes.
- If in doubt, stop and ask rather than guessing.
- Prefer small, reviewable changes.
- Always make sure that tests pass before a task is complete.

---
