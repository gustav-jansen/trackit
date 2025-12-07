"""SQLAlchemy models for trackit database."""

from datetime import datetime, date, UTC
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Date,
    Numeric,
    Boolean,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

Base = declarative_base()


class Account(Base):
    """Bank account model."""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    bank_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    csv_formats = relationship("CSVFormat", back_populates="account", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")


class CSVFormat(Base):
    """CSV format definition model."""

    __tablename__ = "csv_formats"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    is_debit_credit_format = Column(Boolean, default=False, nullable=False)
    negate_debit = Column(Boolean, default=False, nullable=False)
    negate_credit = Column(Boolean, default=False, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="csv_formats")
    column_mappings = relationship(
        "CSVColumnMapping", back_populates="format", cascade="all, delete-orphan"
    )


class CSVColumnMapping(Base):
    """CSV column mapping model."""

    __tablename__ = "csv_column_mappings"

    id = Column(Integer, primary_key=True)
    format_id = Column(Integer, ForeignKey("csv_formats.id"), nullable=False)
    csv_column_name = Column(String, nullable=False)
    db_field_name = Column(String, nullable=False)
    is_required = Column(Boolean, default=False, nullable=False)

    # Relationships
    format = relationship("CSVFormat", back_populates="column_mappings")


class Category(Base):
    """Category model with hierarchical structure."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    """Transaction model."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    unique_id = Column(String, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String, nullable=True)
    reference_number = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    notes = Column(String, nullable=True)
    imported_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Unique constraint on account_id + unique_id
    __table_args__ = (UniqueConstraint("account_id", "unique_id", name="uq_account_unique_id"),)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory."""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

