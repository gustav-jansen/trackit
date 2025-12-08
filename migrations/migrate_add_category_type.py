#!/usr/bin/env python3
"""Migration script to add category_type column to categories table.

This migration adds a category_type column to the categories table:
- category_type (INTEGER, default=0)
  - 0 = Expense (default)
  - 1 = Income
  - 2 = Transfer

The migration sets existing categories to appropriate types:
- "Income" category and all its descendants → type 1 (Income)
- "Transfer" category and all its descendants → type 2 (Transfer)
- All other categories → type 0 (Expense)

Usage:
    python migrations/migrate_add_category_type.py [--db-path PATH]
"""

import sys
from pathlib import Path

# Add src to path so we can import trackit modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text, inspect
from trackit.database.factories import create_sqlite_database
from trackit.database.models import Category


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


def get_all_descendant_ids(session, category_id: int) -> set[int]:
    """Get all descendant category IDs (including the category itself).

    Args:
        session: SQLAlchemy session
        category_id: Category ID to get descendants for

    Returns:
        Set of category IDs including the category and all its descendants
    """
    result = {category_id}

    def collect_children(parent_id: int):
        children = session.query(Category).filter(Category.parent_id == parent_id).all()
        for child in children:
            result.add(child.id)
            collect_children(child.id)

    collect_children(category_id)
    return result


def migrate_database(database_path: str | None = None) -> None:
    """Migrate database to add category_type column and set types.

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
        if "categories" not in inspector.get_table_names():
            raise Exception("Table 'categories' does not exist. Please initialize the database schema first.")

        # Check if column already exists
        if column_exists(engine, "categories", "category_type"):
            print("Migration already applied: category_type column exists in categories table")
            return

        print("Starting migration: adding category_type column...")

        # Add category_type column
        with engine.begin() as conn:
            # SQLite stores INTEGER as INTEGER
            conn.execute(text("ALTER TABLE categories ADD COLUMN category_type INTEGER NOT NULL DEFAULT 0"))
            print("  Added column: category_type")

        print("Setting category types for existing categories...")

        # Now set types for existing categories
        session = db.session_factory()
        try:
            # Find Income category and set it and all descendants to type 1
            income_category = session.query(Category).filter(
                Category.name == "Income",
                Category.parent_id.is_(None)
            ).first()

            if income_category:
                income_ids = get_all_descendant_ids(session, income_category.id)
                session.query(Category).filter(Category.id.in_(income_ids)).update(
                    {"category_type": 1}, synchronize_session=False
                )
                print(f"  Set {len(income_ids)} Income category/categories to type 1 (Income)")

            # Find Transfer category and set it and all descendants to type 2
            transfer_category = session.query(Category).filter(
                Category.name == "Transfer",
                Category.parent_id.is_(None)
            ).first()

            if transfer_category:
                transfer_ids = get_all_descendant_ids(session, transfer_category.id)
                session.query(Category).filter(Category.id.in_(transfer_ids)).update(
                    {"category_type": 2}, synchronize_session=False
                )
                print(f"  Set {len(transfer_ids)} Transfer category/categories to type 2 (Transfer)")

            # All other categories are already set to type 0 (Expense) by default
            # Count how many categories are Expense type
            expense_count = session.query(Category).filter(Category.category_type == 0).count()
            print(f"  {expense_count} category/categories set to type 0 (Expense)")

            session.commit()
        finally:
            session.close()

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
        description="Migrate database to add category_type column"
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
