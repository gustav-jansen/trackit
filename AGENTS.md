# AGENTS.md

This document provides guidance for AI agents working with the Trackit codebase.

## Project Overview

Trackit is a command-line expense tracking application built with Python. It uses a layered architecture with clear separation between CLI, domain logic, and database layers.

## Architecture

### Layer Structure

1. **CLI Layer** (`src/trackit/cli/commands/`): Command-line interface using Click
   - Each command is in its own file
   - Commands register themselves via `register_commands(cli)` function
   - Commands receive database instance via `ctx.obj["db"]`

2. **Domain Services** (`src/trackit/domain/`): Business logic layer
   - Services operate on domain entities (immutable data classes)
   - Services use the Database interface, not direct SQLAlchemy
   - Key services: `TransactionService`, `CategoryService`, `AccountService`, `CSVFormatService`, `CSVImportService`

3. **Domain Entities** (`src/trackit/domain/entities.py`): Immutable data classes
   - Pure Python dataclasses, no database dependencies
   - Represent business concepts: Account, Category, Transaction, CSVFormat, CSVColumnMapping

4. **Database Interface** (`src/trackit/database/base.py`): Abstract repository pattern
   - Defines abstract methods that all database implementations must provide
   - Current implementation: `SQLAlchemyDatabase` in `sqlalchemy_db.py`

5. **Mappers** (`src/trackit/database/mappers.py`): Convert between domain and database models
   - Functions like `account_to_domain()`, `transaction_to_domain()`, etc.
   - Always convert database models to domain models when returning data

6. **Database Models** (`src/trackit/database/models.py`): SQLAlchemy ORM models
   - Represent database schema
   - Should NOT be used directly in domain services or CLI commands

### Key Design Principles

- **Immutable Domain Models**: Domain entities are dataclasses with `frozen=True`
- **Repository Pattern**: All database access goes through the Database interface
- **No Direct SQLAlchemy**: Domain services and CLI commands should never import SQLAlchemy directly
- **Mapper Layer**: Always use mappers to convert between database and domain models

## Common Tasks

### Adding a New CLI Command

1. Create a new file in `src/trackit/cli/commands/` (e.g., `my_command.py`)
2. Import necessary dependencies:
   ```python
   import click
   from trackit.domain.some_service import SomeService
   ```
3. Create command function with `@click.command()` decorator
4. Use `@click.pass_context` to access database: `db = ctx.obj["db"]`
5. Create service instance: `service = SomeService(db)`
6. Add `register_commands(cli)` function at the end
7. Register in `src/trackit/cli/main.py`

### Adding a New Domain Service

1. Create file in `src/trackit/domain/` (e.g., `my_service.py`)
2. Service class should take `Database` instance in `__init__`
3. Methods should operate on domain entities, not database models
4. Use `self.db` to access database methods
5. Always return domain entities, never database models
6. Add lazy import in `src/trackit/domain/__init__.py` if needed

### Adding a New Database Method

1. Add abstract method to `Database` class in `src/trackit/database/base.py`
2. Implement in `SQLAlchemyDatabase` in `src/trackit/database/sqlalchemy_db.py`
3. Method should:
   - Accept domain entities or simple types as parameters
   - Use mappers to convert database models to domain models
   - Return domain entities or simple types

### Adding Date Filtering Options

The codebase has a reusable pattern for date filtering:

1. Use `get_date_range()` from `trackit.utils.date_parser` for period options
2. Use `parse_date()` for relative date strings like "last month", "today"
3. Both commands (`summary` and `transaction list`) support:
   - `--start-date` and `--end-date` for explicit dates
   - Period options: `--this-month`, `--this-year`, `--this-week`, `--last-month`, `--last-year`, `--last-week`
4. Validation: Only one period option at a time, cannot combine with `--start-date`/`--end-date`

Example pattern:
```python
from trackit.utils.date_parser import parse_date, get_date_range

# Validate period options
period_options = [this_month, this_year, this_week, last_month, last_year, last_week]
period_count = sum(period_options)

if period_count > 1:
    click.echo("Error: Only one period option can be specified at a time.", err=True)
    ctx.exit(1)

if period_count > 0 and (start_date or end_date):
    click.echo("Error: Period options cannot be combined with --start-date or --end-date.", err=True)
    ctx.exit(1)

# Parse dates
start = None
end = None

if period_count == 1:
    if this_month:
        start, end = get_date_range("this-month")
    # ... handle other periods
else:
    if start_date:
        start = parse_date(start_date)
    if end_date:
        end = parse_date(end_date)
```

## Testing Patterns

### Test Structure

- Tests are in `tests/` directory
- Use pytest fixtures from `tests/conftest.py`:
  - `cli_runner`: Click test runner
  - `temp_db`: Temporary database instance
  - `sample_account`: Pre-created test account
  - `sample_categories`: Pre-created test categories
  - `transaction_service`: TransactionService instance
  - `category_service`: CategoryService instance

### Writing Tests

1. Test files follow pattern: `test_<module>.py`
2. Test functions: `def test_<feature>_<scenario>(cli_runner, temp_db, ...)`
3. Use `cli_runner.invoke()` to test CLI commands
4. Assert on `result.exit_code` and `result.output`
5. Create test data using services, not direct database access

Example:
```python
def test_my_command(cli_runner, temp_db, sample_account):
    result = cli_runner.invoke(
        cli,
        ["--db-path", temp_db.database_path, "my-command", "--option", "value"]
    )
    assert result.exit_code == 0
    assert "expected output" in result.output
```

### Running Tests

```bash
# All tests
uv run pytest tests/

# Specific test file
uv run pytest tests/test_transaction.py

# Specific test
uv run pytest tests/test_transaction.py::test_transaction_list_this_month

# With coverage
uv run pytest --cov=trackit tests/
```

## Important Files

### Core Files

- `src/trackit/cli/main.py`: CLI entry point, registers all commands
- `src/trackit/database/base.py`: Database interface (abstract base class)
- `src/trackit/database/sqlalchemy_db.py`: SQLAlchemy implementation
- `src/trackit/database/models.py`: SQLAlchemy ORM models
- `src/trackit/database/mappers.py`: Domain ↔ Database conversion
- `src/trackit/domain/entities.py`: Domain model definitions
- `src/trackit/database/factories.py`: Database factory function

### Utility Files

- `src/trackit/utils/date_parser.py`: Date parsing and period range calculation
- `src/trackit/utils/amount_parser.py`: Amount parsing (handles various formats)
- `src/trackit/utils/account_resolver.py`: Resolve account by name or ID

### Command Files

Each command is in `src/trackit/cli/commands/`:
- `account.py`: Account management
- `category.py`: Category management
- `transaction.py`: Transaction management (list, update, delete)
- `add.py`: Add single transaction
- `categorize.py`: Categorize transactions
- `summary.py`: Category summaries
- `format.py`: CSV format management
- `import_cmd.py`: CSV import
- `init_categories.py`: Initialize default categories

## Code Conventions

### Imports

- Group imports: standard library, third-party, local
- Use absolute imports: `from trackit.domain.transaction import TransactionService`
- Avoid circular dependencies (use lazy imports in `__init__.py` if needed)

### Type Hints

- Use type hints for function parameters and return types
- Domain entities use `Optional[T]` for nullable fields
- Use `tuple[date, date]` for date ranges (Python 3.9+ syntax)

### Error Handling

- CLI commands should use `click.echo(..., err=True)` for errors
- Use `ctx.exit(1)` to exit with error code
- Services raise `ValueError` for invalid operations
- Database methods return `None` for "not found" cases

### Date Handling

- Always use `date` objects, not `datetime`
- Use `date.today()` for current date
- Use `relativedelta` from `dateutil` for month/year calculations
- Use `timedelta` for day calculations

### Amount Handling

- Use `Decimal` for all monetary amounts
- Parse amounts with `parse_amount()` from `utils/amount_parser`
- Store as `Decimal` in database

### Code Formatting

- **No trailing whitespace**: Never leave spaces at the end of lines
- Remove trailing whitespace before committing changes
- Use `sed -i 's/[[:space:]]*$//' <file>` or similar to clean trailing spaces

## Common Patterns

### Category Filtering

When filtering by category path:
- Summary command includes all descendants (uses `_get_all_descendant_ids()`)
- Transaction list filters by exact category only
- Use `db.get_category_by_path(path)` to resolve category
- Use `db._get_all_descendant_ids(category_id)` to get descendants

### Transaction Filtering

Transactions can be filtered by:
- Date range: `start_date`, `end_date`
- Category: `category_id` or `category_path`
- Account: `account_id`
- Uncategorized: `uncategorized=True`

### Category Types

Categories have types:
- `0` or `None`: Expense (default)
- `1`: Income
- `2`: Transfer (excluded from summary by default)

## Database Schema

### Key Tables

- `accounts`: Bank accounts
- `categories`: Category hierarchy (self-referential via `parent_id`)
- `transactions`: Financial transactions
- `csv_formats`: CSV format definitions
- `csv_column_mappings`: Column mappings for CSV formats

### Relationships

- `transactions.account_id` → `accounts.id`
- `transactions.category_id` → `categories.id`
- `categories.parent_id` → `categories.id` (self-referential)
- `csv_formats.account_id` → `accounts.id`
- `csv_column_mappings.format_id` → `csv_formats.id`

## Migration Notes

- Migrations are in `migrations/` directory
- Use SQLAlchemy migrations for schema changes
- Always test migrations on sample data

## Development Workflow

1. **Make Changes**: Edit code following conventions above
2. **Write Tests**: **ALWAYS** add tests for new functionality - no exceptions
3. **Run Tests**: `uv run pytest tests/` - **ALWAYS** ensure all tests pass before completing changes
4. **Update Documentation**: **ALWAYS** update README.md when adding new functionality
5. **Check Formatting**: Ensure no trailing whitespace or style issues
6. **Verify**: Run full test suite to ensure no regressions: `uv run pytest tests/`

### Mandatory Requirements

- **Tests are mandatory**: Every new feature, command, or significant change must have corresponding tests
- **Tests must pass**: Never commit code that breaks existing tests or fails new tests
- **Documentation is mandatory**: Always update README.md when adding:
  - New commands or options
  - New features
  - Changes to existing functionality
  - New examples or usage patterns
- **No trailing whitespace**: Clean all trailing spaces before completing work

## Common Pitfalls

1. **Don't use SQLAlchemy models directly** in domain services or CLI commands
2. **Always use mappers** when converting between database and domain models
3. **Don't mutate domain entities** (they're frozen)
4. **Use Database interface**, not SQLAlchemyDatabase directly in services
5. **Test with temporary databases** - tests use `temp_db` fixture
6. **Don't skip tests** - every feature needs tests
7. **Don't forget to update README.md** - documentation is part of the feature
8. **Don't leave trailing whitespace** - clean code before completing

## Questions to Ask

When working on a feature, consider:
- Does it need a new domain service or can it use existing ones?
- Should it be a new command or part of an existing command?
- Does it need database schema changes?
- What domain entities does it work with?
- How should errors be handled?
- What tests are needed?

## Getting Help

- Check existing similar commands for patterns
- Look at test files for usage examples
- Review domain services to understand business logic
- Check database interface for available methods
