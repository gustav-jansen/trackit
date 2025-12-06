"""Database factory functions for creating database instances."""

import os
from pathlib import Path
from typing import Optional

from trackit.database.sqlalchemy_db import SQLAlchemyDatabase


def create_sqlite_database(database_path: Optional[str] = None) -> SQLAlchemyDatabase:
    """Create a SQLite database instance.

    Args:
        database_path: Path to SQLite database file. If None, checks TRACKIT_DB_PATH
            environment variable, then defaults to ~/.trackit/trackit.db

    Returns:
        SQLAlchemyDatabase instance configured for SQLite
    """
    if database_path is None:
        # Check environment variable
        database_path = os.environ.get("TRACKIT_DB_PATH")

    if database_path is None:
        # Default to ~/.trackit/trackit.db
        home = Path.home()
        db_dir = home / ".trackit"
        db_dir.mkdir(exist_ok=True)
        database_path = str(db_dir / "trackit.db")

    database_url = f"sqlite:///{database_path}"
    return SQLAlchemyDatabase(database_url)

