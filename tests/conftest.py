"""Shared pytest fixtures for trackit tests."""

import tempfile
import os
from pathlib import Path
import pytest

from trackit.database.factories import create_sqlite_database
from trackit.domain.account import AccountService
from trackit.domain.csv_format import CSVFormatService
from trackit.domain.category import CategoryService
from trackit.domain.transaction import TransactionService


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temporary file for the database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Create database
    db = create_sqlite_database(database_path=db_path)
    # Store the path for tests that need it
    db.database_path = db_path
    db.connect()
    db.initialize_schema()
    
    yield db
    
    # Cleanup
    db.disconnect()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def account_service(temp_db):
    """Create an AccountService with a temporary database."""
    return AccountService(temp_db)


@pytest.fixture
def csv_format_service(temp_db):
    """Create a CSVFormatService with a temporary database."""
    return CSVFormatService(temp_db)


@pytest.fixture
def category_service(temp_db):
    """Create a CategoryService with a temporary database."""
    return CategoryService(temp_db)


@pytest.fixture
def transaction_service(temp_db):
    """Create a TransactionService with a temporary database."""
    return TransactionService(temp_db)


@pytest.fixture
def sample_account(account_service):
    """Create a sample account for testing."""
    account_id = account_service.create_account(name="Test Account", bank_name="Test Bank")
    return account_service.get_account(account_id)


@pytest.fixture
def sample_categories(category_service):
    """Initialize categories and return some sample category IDs."""
    # Initialize default categories
    from trackit.cli.commands.init_categories import INITIAL_CATEGORIES
    
    category_ids = {}
    
    # Create root categories first
    for category_name, parent_name in INITIAL_CATEGORIES:
        if parent_name is None:
            category_id = category_service.create_category(name=category_name, parent_path=None)
            category_ids[category_name] = category_id
    
    # Create child categories
    for category_name, parent_name in INITIAL_CATEGORIES:
        if parent_name is not None:
            category_id = category_service.create_category(
                name=category_name, parent_path=parent_name
            )
            category_ids[f"{parent_name} > {category_name}"] = category_id
    
    return category_ids


@pytest.fixture
def sample_csv_format(csv_format_service, sample_account):
    """Create a sample CSV format with mappings."""
    format_id = csv_format_service.create_format(
        name="Test Format", account_id=sample_account.id
    )
    
    # Add required mappings
    csv_format_service.add_mapping(format_id, "Transaction ID", "unique_id", is_required=True)
    csv_format_service.add_mapping(format_id, "Date", "date", is_required=True)
    csv_format_service.add_mapping(format_id, "Amount", "amount", is_required=True)
    csv_format_service.add_mapping(format_id, "Description", "description")
    csv_format_service.add_mapping(format_id, "Reference", "reference_number")
    
    return csv_format_service.get_format(format_id)


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    from click.testing import CliRunner
    
    return CliRunner()


@pytest.fixture
def fixtures_dir():
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"

