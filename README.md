# Trackit

A command-line expense tracking application that helps you import, categorize, and analyze your financial transactions from multiple bank accounts.

## Features

- **Multi-Account Support**: Track expenses across multiple bank accounts
- **CSV Import**: Import transactions from CSV files with configurable column mappings for different bank formats
- **Flexible Categorization**: Unlimited depth category hierarchy for organizing expenses
- **Transaction Management**: Add transactions manually or import from CSV files
- **Duplicate Detection**: Automatically prevents importing duplicate transactions
- **Time Period Analysis**: View and summarize transactions for any date range
- **Category Summaries**: Get expense breakdowns by category with totals
- **Immutable Transaction Data**: Transaction details are protected from accidental modification
- **Editable Notes & Categories**: Update transaction categories and notes as needed

## Installation

### Prerequisites

- Python 3.12 or higher
- `uv` package manager (recommended) or `pip`

### Install with uv

```bash
# Clone the repository
git clone <repository-url>
cd trackit

# Install dependencies
uv sync
```

### Install with pip

```bash
# Clone the repository
git clone <repository-url>
cd trackit

# Install in development mode
pip install -e .
```

## Quick Start

1. **Initialize categories** (optional, but recommended):
   ```bash
   trackit init-categories
   ```

2. **Create an account**:
   ```bash
   trackit account create "Chase"
   # or with explicit bank name
   trackit account create "My Checking" --bank "Chase"
   ```

   You can rename or delete accounts later:
   ```bash
   trackit account rename "Chase" "Chase Checking"
   trackit account delete "Old Account"  # Only if no transactions/formats
   ```

3. **Create a CSV format** for your bank's export format:
   ```bash
   trackit format create "Chase Format" --account "Chase"
   # or use account ID: trackit format create "Chase Format" --account 1
   ```

4. **Map CSV columns** to database fields:
   ```bash
   trackit format map "Chase Format" "Transaction ID" unique_id --required
   trackit format map "Chase Format" "Date" date --required
   trackit format map "Chase Format" "Amount" amount --required
   trackit format map "Chase Format" "Description" description
   ```

5. **Import transactions**:
   ```bash
   trackit import transactions.csv --format "Chase Format"
   ```

6. **View transactions**:
   ```bash
   trackit transaction list
   trackit transaction list --start-date 2024-01-01 --end-date 2024-01-31
   trackit transaction list --category "Food & Dining > Groceries" --verbose
   trackit transaction list --account "Chase" --uncategorized
   trackit transaction list --start-date "last month" --end-date "today"
   ```

7. **Categorize transactions**:
   ```bash
   trackit categorize 1 "Food & Dining > Groceries"
   trackit categorize 1 2 3 4 5 "Food & Dining > Groceries"  # Multiple transactions
   ```

8. **View summaries**:
   ```bash
   trackit summary
   trackit summary --start-date 2024-01-01 --end-date 2024-01-31
   ```

9. **Manage transactions and formats**:
   ```bash
   # Update a transaction
   trackit transaction update 1 --amount -75.00 --category "Food & Dining > Groceries"
   trackit transaction update 1 --account "Chase"  # Reassign to different account

   # Delete a transaction
   trackit transaction delete 1

   # Update a CSV format
   trackit format update "Chase Format" --name "Chase New Format"
   trackit format update "Chase Format" --account "Wells Fargo"  # Reassign to different account

   # Delete a CSV format
   trackit format delete "Old Format"
   ```

**Note**: To delete an account, you must first delete or reassign all its transactions and CSV formats. This prevents accidental data loss.

## Commands

### Account Management

- `trackit account create <name> [--bank <bank_name>]` - Create a new account
- `trackit account list` - List all accounts
- `trackit account rename <name_or_id> <new_name> [--bank <bank_name>]` - Rename an account
- `trackit account delete <name_or_id>` - Delete an account (only if no transactions/formats)

### CSV Format Management

- `trackit format create <name> --account <name_or_id>` - Create a CSV format
- `trackit format map <format_name> <csv_column> <db_field> [--required]` - Map CSV columns
- `trackit format list [--account <name_or_id>]` - List CSV formats
- `trackit format show <format_name>` - Show format details
- `trackit format update <format_name> [--name <new_name>] [--account <account>]` - Update format name or account
- `trackit format delete <format_name>` - Delete a CSV format

### Transaction Management

- `trackit import <csv_file> --format <format_name>` - Import transactions from CSV
- `trackit add --account <name_or_id> --date <date> --amount <amount> [options]` - Add transaction manually
- `trackit transaction list [--start-date <date>] [--end-date <date>] [--category <path>] [--account <name_or_id>] [--uncategorized] [--verbose]` - View transactions
- `trackit categorize <transaction_id> [transaction_id ...] <category_path>` - Assign category to one or more transactions
- `trackit notes <transaction_id> [<notes>] [--clear]` - Update transaction notes
- `trackit transaction update <id> [--account <account>] [--date <date>] [--amount <amount>] [--description <desc>] [--reference <ref>] [--category <category>] [--notes <notes>]` - Update transaction fields
- `trackit transaction delete <id>` - Delete a transaction

**Note**: Account can be specified by name or ID in most commands. Dates support relative formats like `today`, `yesterday`, `last month`, `this year`, etc.

### Category Management

- `trackit init-categories` - Initialize default category tree
- `trackit category list` - List all categories
- `trackit category create <name> [--parent <parent_path>]` - Create a category

### Analysis

- `trackit summary [--start-date <date>] [--end-date <date>] [--category <path>]` - Show category summary

**Note**: Dates support relative formats like `today`, `yesterday`, `last month`, `this year`, etc.

## Database

By default, the database is stored at `~/.trackit/trackit.db`. You can override this location using:

- **Environment variable**: Set `TRACKIT_DB_PATH` to your desired database path
- **CLI option**: Use `--db-path <path>` with any command

Example:
```bash
export TRACKIT_DB_PATH=/path/to/custom.db
trackit account list

# or
trackit --db-path /path/to/custom.db account list
```

## CSV Import Format

When creating a CSV format, you need to map at least these required fields:
- `date` - Transaction date
- `amount` - Transaction amount (supports various formats: `$123.45`, `-123.45`, `(123.45)`, etc.)

Optional fields:
- `unique_id` - Unique transaction identifier (prevents duplicates). If not provided, a unique ID will be automatically generated from the date, description, and amount fields.
- `description` - Transaction description (required if `unique_id` is not mapped, as it's used to generate the unique ID)
- `reference_number` - Reference number

**Note**: If your CSV file doesn't have a unique transaction ID column, you can omit the `unique_id` mapping. The system will automatically generate a unique ID based on the combination of date, description, and amount. In this case, the `description` field becomes required to ensure reliable duplicate detection.

**Example formats**:

With unique_id:
```bash
trackit format map "Chase Format" "Transaction ID" unique_id --required
trackit format map "Chase Format" "Date" date --required
trackit format map "Chase Format" "Amount" amount --required
```

Without unique_id (auto-generated):
```bash
trackit format map "Bank Format" "Transaction Date" date --required
trackit format map "Bank Format" "Amount" amount --required
trackit format map "Bank Format" "Description" description  # Required when unique_id not mapped
```

The account is automatically determined from the format's associated account, so you don't need to map `account_name` from the CSV.

### Debit/Credit Format

Some banks export CSV files where transaction amounts are split into separate `Debit` and `Credit` columns instead of a single `Amount` column. Trackit supports this format with configurable negation options.

**Creating a debit/credit format**:
```bash
trackit format create "Credit Card Format" --account "My Credit Card" \
  --debit-credit-format \
  --negate-debit \
  --negate-credit
```

**Mapping debit/credit columns**:
```bash
trackit format map "Credit Card Format" "Date" date --required
trackit format map "Credit Card Format" "Debit" debit --required
trackit format map "Credit Card Format" "Credit" credit --required
trackit format map "Credit Card Format" "Description" description
```

**How it works**:
- Each row must have exactly one value in either the `Debit` or `Credit` column (not both, not neither)
- The `--negate-debit` flag negates debit values (e.g., positive debit `19.74` → negative amount `-19.74`)
- The `--negate-credit` flag negates credit values (e.g., negative credit `-1482.17` → positive amount `1482.17`)
- The final amount stored in the database is calculated from whichever column has a value, with negation applied if configured

**Example CSV format**:
```csv
Status,Date,Description,Debit,Credit,Member Name
Cleared,11/26/2025,"Microsoft*One Month Membe425-6816830 WA",19.74,,GUSTAV R JANSEN
Cleared,11/19/2025,"ONLINE PAYMENT, THANK YOU",,-1482.17,GUSTAV R JANSEN
```

With `--negate-debit` and `--negate-credit` enabled:
- First row: Debit `19.74` → stored as `-19.74` (charge)
- Second row: Credit `-1482.17` → stored as `1482.17` (payment)

**Updating format flags**:
```bash
trackit format update "Credit Card Format" --negate-debit  # Enable debit negation
trackit format update "Credit Card Format" --no-negate-debit  # Disable debit negation
```

**Note**: Debit/credit format and regular amount format are mutually exclusive. You cannot map both `amount` and `debit`/`credit` fields in the same format.

## Category Hierarchy

Categories support unlimited depth. Use `>` to separate levels in category paths:
- `Food & Dining`
- `Food & Dining > Groceries`
- `Food & Dining > Restaurants > Fast Food`

## Features

### Account Name Resolution

Most commands that accept an account ID also accept an account name for convenience:
```bash
trackit add --account "Chase" --date today --amount -50.00
trackit transaction list --account "Chase"
trackit format create "My Format" --account "Chase"
```

### Relative Dates

The date parser supports relative dates for easier filtering:
- **Simple**: `today`, `yesterday`, `tomorrow`
- **Time periods**: `last month`, `this month`, `next month`
- **Years**: `last year`, `this year`, `next year`
- **Weeks**: `last week`, `this week`, `next week`
- **Days of week**: `last monday`, `last tuesday`, etc.

Examples:
```bash
trackit transaction list --start-date "last month" --end-date "today"
trackit summary --start-date "this year"
trackit add --account "Chase" --date "yesterday" --amount -25.00
```

### Uncategorized Transactions

Filter to see only transactions that haven't been categorized:
```bash
trackit transaction list --uncategorized
```

### Transaction Totals

The `transaction list` command automatically displays totals at the bottom:
- Total expenses (sum of negative amounts)
- Total income (sum of positive amounts)
- Transaction count

## Development

### Running Tests

```bash
# Install test dependencies
uv sync --extra test

# Run all tests
pytest

# Run with coverage
pytest --cov=trackit

# Run specific test file
pytest tests/test_account.py
```

Tests use isolated temporary databases and won't affect your production data.

### Project Structure

```
trackit/
├── src/trackit/
│   ├── database/          # Database abstraction and SQLite implementation
│   ├── domain/            # Business logic layer
│   ├── cli/               # Command-line interface
│   └── utils/             # Utility functions
├── tests/                 # Test suite
│   ├── fixtures/          # Test data files
│   └── test_*.py          # Test files
└── pyproject.toml         # Project configuration
```

## Architecture

The application follows a layered architecture designed for maintainability and future extensibility:

### Layers

1. **CLI Layer** (`cli/commands/*`): Command-line interface and presentation logic
2. **Domain Services** (`domain/*.py`): Business logic layer that operates on domain models
3. **Domain Models** (`domain/entities.py`): Immutable data classes representing business concepts
4. **Database Interface** (`database/base.py`): Abstract repository interface
5. **Database Implementation** (`database/sqlite.py`): SQLite-specific implementation
6. **Mappers** (`database/mappers.py`): Conversion layer between domain models and database models
7. **Database Models** (`database/models.py`): SQLAlchemy ORM models (database schema)

### Key Design Principles

- **Domain Models**: Pure, immutable data classes independent of database schema
- **Repository Pattern**: Database operations abstracted through a clean interface
- **Mapper Layer**: Isolates conversion logic between domain and database models
- **Separation of Concerns**: Business logic is completely isolated from database implementation

### Benefits

- **Future-Proof**: The architecture is prepared for a future switch to double-entry bookkeeping. Only the database models and mappers need to change, while business logic and UI remain stable.
- **Type Safety**: Domain models provide strong typing and IDE support
- **Testability**: Domain models can be easily mocked and tested independently
- **Maintainability**: Clear boundaries between layers make the codebase easier to understand and modify

This separation makes it easy to:
- Add a web interface or other UIs without changing business logic
- Switch database backends (SQLite → PostgreSQL, etc.)
- Evolve the data model (single-entry → double-entry bookkeeping) with minimal impact on business logic

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

[Add contribution guidelines here]

