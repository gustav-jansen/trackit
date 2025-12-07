"""Summary commands."""

import click
from trackit.domain.transaction import TransactionService
from trackit.domain.category import CategoryService
from trackit.utils.date_parser import parse_date


def _get_filtered_transactions(db, start_date, end_date, category_path, include_transfers):
    """Get filtered transactions matching the summary criteria."""
    from trackit.database.sqlalchemy_db import SQLAlchemyDatabase
    from sqlalchemy import or_
    from trackit.database.models import Transaction

    # Access SQLAlchemy database methods for filtering
    if not isinstance(db, SQLAlchemyDatabase):
        raise ValueError("Database must be SQLAlchemyDatabase")

    session = db._get_session()
    query = session.query(Transaction)

    # Apply date filters
    if start_date is not None:
        query = query.filter(Transaction.date >= start_date)
    if end_date is not None:
        query = query.filter(Transaction.date <= end_date)

    # Apply category filter if specified
    if category_path is not None:
        category = db.get_category_by_path(category_path)
        if category is not None:
            descendant_ids = db._get_all_descendant_ids(category.id)
            query = query.filter(Transaction.category_id.in_(descendant_ids))

    # Filter out Transfer category transactions if not including transfers
    if not include_transfers:
        transfer_category = db.get_category_by_path("Transfer")
        if transfer_category is not None:
            transfer_ids = db._get_all_descendant_ids(transfer_category.id)
            query = query.filter(
                or_(Transaction.category_id.is_(None), ~Transaction.category_id.in_(transfer_ids))
            )

    return query.all()


def _calculate_category_total(db, category_id, transactions):
    """Calculate total for a category including all its descendants."""
    if category_id is None:
        # Uncategorized transactions
        return sum(float(txn.amount) for txn in transactions if txn.category_id is None)

    # Get all descendant IDs including the category itself
    descendant_ids = db._get_all_descendant_ids(category_id)
    return sum(float(txn.amount) for txn in transactions if txn.category_id in descendant_ids)


def _display_expanded_summary(db, category_tree, transactions, indent=0, is_first=True):
    """Recursively display category tree with totals, sorted by value (highest first)."""
    # Sort categories by total value (descending), then by name for ties
    def get_sort_key(cat):
        total = _calculate_category_total(db, cat["id"], transactions)
        return (-abs(total), cat["name"])  # Negative abs for descending order

    sorted_categories = sorted(category_tree, key=get_sort_key)

    # Use 4 spaces per indent level for larger indentation
    INDENT_SIZE = 4

    for i, cat in enumerate(sorted_categories):
        total = _calculate_category_total(db, cat["id"], transactions)

        # Skip categories with no transactions (total includes all descendants)
        if total == 0:
            continue

        # Add blank line before top-level categories (except the first one)
        if indent == 0 and not (is_first and i == 0):
            click.echo()

        indent_str = " " * (INDENT_SIZE * indent)
        category_name = cat["name"]
        total_str = f"${total:,.2f}"
        # Calculate available width for category name (50 - indent length)
        category_width = 50 - (INDENT_SIZE * indent)
        # Amount should move right as indent increases (deeper categories have values more to the right)
        # Base amount position is 20 chars from right, add indent to move it further right
        amount_width = 20 + (INDENT_SIZE * indent)
        click.echo(f"{indent_str}{category_name:<{category_width}} {total_str:>{amount_width}}")

        # Display children recursively (they will be sorted in the recursive call)
        if cat.get("children"):
            _display_expanded_summary(db, cat["children"], transactions, indent + 1, is_first=False)


@click.command("summary")
@click.option("--start-date", help="Start date (YYYY-MM-DD or relative like 'last month', 'this year')")
@click.option("--end-date", help="End date (YYYY-MM-DD or relative like 'today', 'this month')")
@click.option("--category", help="Category path (e.g., 'Food & Dining > Groceries')")
@click.option("--include-transfers", is_flag=True, help="Include transactions with Transfer category")
@click.option("--expand", is_flag=True, help="Expand entire category tree with subtotals")
@click.pass_context
def summary(ctx, start_date: str, end_date: str, category: str, include_transfers: bool, expand: bool):
    """Show category summary."""
    db = ctx.obj["db"]
    service = TransactionService(db)

    # Parse dates
    start = None
    if start_date:
        try:
            start = parse_date(start_date)
        except ValueError as e:
            click.echo(f"Error: Invalid start date: {e}", err=True)
            ctx.exit(1)

    end = None
    if end_date:
        try:
            end = parse_date(end_date)
        except ValueError as e:
            click.echo(f"Error: Invalid end date: {e}", err=True)
            ctx.exit(1)

    # Get filtered transactions for overall total calculation
    filtered_transactions = _get_filtered_transactions(db, start, end, category, include_transfers)

    if not filtered_transactions:
        click.echo("No transactions found.")
        return

    # Calculate overall total from all filtered transactions
    overall_total = sum(float(txn.amount) for txn in filtered_transactions)

    if expand:
        # Expanded view: show full category tree
        category_service = CategoryService(db)

        # If category filter is specified, only show that category's subtree
        if category:
            category_obj = db.get_category_by_path(category)
            if category_obj:
                # Build subtree starting from the filtered category
                def build_subtree(cat_id):
                    cat = db.get_category(cat_id)
                    if cat is None:
                        return None
                    children = category_service.list_categories(parent_id=cat_id)
                    child_trees = [build_subtree(child.id) for child in children]
                    child_trees = [ct for ct in child_trees if ct is not None]
                    return {
                        "id": cat.id,
                        "name": cat.name,
                        "parent_id": cat.parent_id,
                        "created_at": cat.created_at,
                        "children": child_trees
                    }
                category_tree = [build_subtree(category_obj.id)] if build_subtree(category_obj.id) else []
            else:
                category_tree = []
        else:
            category_tree = category_service.get_category_tree()

        # Also include uncategorized if there are any
        has_uncategorized = any(txn.category_id is None for txn in filtered_transactions)

        click.echo("\nCategory Summary (Expanded):")
        click.echo("-" * 80)
        click.echo(f"{'Category':<50} {'Total':>20}")
        click.echo("-" * 80)

        # Display category tree
        if category_tree:
            _display_expanded_summary(db, category_tree, filtered_transactions, indent=0, is_first=True)

        # Display uncategorized if present
        if has_uncategorized:
            uncategorized_total = _calculate_category_total(db, None, filtered_transactions)
            total_str = f"${uncategorized_total:,.2f}" if uncategorized_total != 0 else "-"
            click.echo(f"{'Uncategorized':<50} {total_str:>20}")
    else:
        # Standard view: show top-level categories (or subcategories if category filter is specified)
        summaries = service.get_summary(
            start_date=start, end_date=end, category_path=category, include_transfers=include_transfers
        )

        if not summaries:
            click.echo("No transactions found.")
            return

        # Display summary
        click.echo("\nCategory Summary:")
        click.echo("-" * 80)
        click.echo(f"{'Category':<50} {'Total':>20}")
        click.echo("-" * 80)

        # Sort by absolute value (descending), then by name for ties
        for s in sorted(summaries, key=lambda x: (-abs(x["expenses"] + x["income"]), x["category_name"] or "")):
            total = s["expenses"] + s["income"]  # Net total
            # Skip categories with no transactions
            if total == 0:
                continue
            category_name = s["category_name"] or "Uncategorized"
            total_str = f"${total:,.2f}"
            click.echo(f"{category_name:<50} {total_str:>20}")

    click.echo("-" * 80)
    total_str = f"${overall_total:,.2f}" if overall_total != 0 else "-"
    click.echo(f"{'TOTAL':<50} {total_str:>20}")


def register_commands(cli):
    """Register summary command with main CLI."""
    cli.add_command(summary)

