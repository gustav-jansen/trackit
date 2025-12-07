# Database Migrations

This directory contains database migration scripts for trackit.

## Running Migrations

### Migration: Add Debit/Credit Format Support

This migration adds support for CSV formats with separate debit and credit columns.

**To run the migration:**

```bash
# Using default database location (~/.trackit/trackit.db)
python migrations/migrate_add_debit_credit_format.py

# Using custom database path
python migrations/migrate_add_debit_credit_format.py --db-path /path/to/trackit.db

# Using environment variable
export TRACKIT_DB_PATH=/path/to/trackit.db
python migrations/migrate_add_debit_credit_format.py
```

**What it does:**
- Adds `is_debit_credit_format` column (BOOLEAN, default=False)
- Adds `negate_debit` column (BOOLEAN, default=False)
- Adds `negate_credit` column (BOOLEAN, default=False)

**Safety:**
- The migration is idempotent - it checks if columns already exist before adding them
- Existing CSV formats will have all new columns set to False (default values)
- No data loss - this only adds new columns

**Note:** Always backup your database before running migrations on production data.
