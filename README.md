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
   trackit view
   trackit view --start-date 2024-01-01 --end-date 2024-01-31
   trackit view --category "Food & Dining > Groceries" --verbose
   trackit view --account "Chase" --uncategorized
   trackit view --start-date "last month" --end-date "today"
   ```

7. **Categorize transactions**:
   ```bash
   trackit categorize 1 "Food & Dining > Groceries"
   ```

8. **View summaries**:
   ```bash
   trackit summary
   trackit summary --start-date 2024-01-01 --end-date 2024-01-31
   ```

## Commands

### Account Management

- `trackit account create <name> [--bank <bank_name>]` - Create a new account
- `trackit account list` - List all accounts

### CSV Format Management

- `trackit format create <name> --account <name_or_id>` - Create a CSV format
- `trackit format map <format_name> <csv_column> <db_field> [--required]` - Map CSV columns
- `trackit format list [--account <name_or_id>]` - List CSV formats
- `trackit format show <format_name>` - Show format details

### Transaction Management

- `trackit import <csv_file> --format <format_name>` - Import transactions from CSV
- `trackit add --account <name_or_id> --date <date> --amount <amount> [options]` - Add transaction manually
- `trackit view [--start-date <date>] [--end-date <date>] [--category <path>] [--account <name_or_id>] [--uncategorized] [--verbose]` - View transactions
- `trackit categorize <transaction_id> <category_path>` - Assign category to transaction
- `trackit notes <transaction_id> [<notes>] [--clear]` - Update transaction notes

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
- `unique_id` - Unique transaction identifier (prevents duplicates)
- `date` - Transaction date
- `amount` - Transaction amount (supports various formats: `$123.45`, `-123.45`, `(123.45)`, etc.)

Optional fields:
- `description` - Transaction description
- `reference_number` - Reference number

The account is automatically determined from the format's associated account, so you don't need to map `account_name` from the CSV.

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
trackit view --account "Chase"
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
trackit view --start-date "last month" --end-date "today"
trackit summary --start-date "this year"
trackit add --account "Chase" --date "yesterday" --amount -25.00
```

### Uncategorized Transactions

Filter to see only transactions that haven't been categorized:
```bash
trackit view --uncategorized
```

### Transaction Totals

The `view` command automatically displays totals at the bottom:
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

The application follows a layered architecture:

- **Database Layer**: Abstract interface with SQLite implementation (easily switchable)
- **Domain Layer**: Business logic separated from UI
- **CLI Layer**: Command-line interface (extendable to web UI later)

This separation makes it easy to add a web interface or other UIs in the future without changing the core business logic.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

