#!/usr/bin/env python3
"""Migration script to add debit/credit format columns to csv_formats table.

This migration adds three new columns to the csv_formats table:
- is_debit_credit_format (BOOLEAN, default=False)
- negate_debit (BOOLEAN, default=False)
- negate_credit (BOOLEAN, default=False)

Usage:
    python migrations/migrate_add_debit_credit_format.py [--db-path PATH]
"""

import sys
import os
from pathlib import Path

# Add src to path so we can import trackit modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text, inspect
from trackit.database.factories import create_sqlite_database


def column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table.

    Args:
        engine: SQLAlchemy engine
        table_name: Name of the table
        column_name: Name of the column

    Returns:
        True if column exists, False otherwise
    """
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_database(database_path: str | None = None) -> None:
    """Migrate database to add debit/credit format columns.

    Args:
        database_path: Path to database file. If None, uses default location.

    Raises:
        Exception: If migration fails
    """
    # Create database instance
    db = create_sqlite_database(database_path=database_path)
    db.connect()

    try:
        # Get engine from sessionmaker by creating a session and accessing its bind
        session = db.session_factory()
        try:
            engine = session.bind
            if engine is None:
                raise Exception("Could not get database engine from session")
        finally:
            session.close()

        # Check if table exists
        inspector = inspect(engine)
        if "csv_formats" not in inspector.get_table_names():
            raise Exception("Table 'csv_formats' does not exist. Please initialize the database schema first.")

        # Check if columns already exist
        if column_exists(engine, "csv_formats", "is_debit_credit_format"):
            print("Migration already applied: columns exist in csv_formats table")
            return

        print("Starting migration: adding debit/credit format columns...")

        # Add columns one by one
        with engine.begin() as conn:
            # SQLite supports ALTER TABLE ADD COLUMN with DEFAULT since version 3.25.0
            # For older versions, we'd need a more complex migration, but modern SQLite
            # (which Python uses) supports this syntax.

            # Add is_debit_credit_format column
            # SQLite stores BOOLEAN as INTEGER (0 or 1)
            conn.execute(text("ALTER TABLE csv_formats ADD COLUMN is_debit_credit_format INTEGER NOT NULL DEFAULT 0"))
            print("  Added column: is_debit_credit_format")

            # Add negate_debit column
            conn.execute(text("ALTER TABLE csv_formats ADD COLUMN negate_debit INTEGER NOT NULL DEFAULT 0"))
            print("  Added column: negate_debit")

            # Add negate_credit column
            conn.execute(text("ALTER TABLE csv_formats ADD COLUMN negate_credit INTEGER NOT NULL DEFAULT 0"))
            print("  Added column: negate_credit")

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        db.disconnect()


def main():
    """Main entry point for migration script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate database to add debit/credit format columns"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to database file (overrides TRACKIT_DB_PATH environment variable)",
    )
    args = parser.parse_args()

    try:
        migrate_database(database_path=args.db_path)
        return 0
    except Exception as e:
        print(f"\nMigration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
