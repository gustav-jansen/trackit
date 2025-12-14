"""Summary commands."""

import click
from trackit.domain.transaction import TransactionService
from trackit.domain.category import CategoryService
from trackit.utils.date_parser import parse_date, get_date_range


def _get_filtered_transactions(db, start_date, end_date, category_path, include_transfers):
    """Get filtered transactions matching the summary criteria."""
    from trackit.database.sqlalchemy_db import SQLAlchemyDatabase
    from sqlalchemy import or_
    from trackit.database.models import Transaction, Category

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

    # Filter out Transfer type category transactions if not including transfers
    if not include_transfers:
        # Get all categories with type 2 (Transfer) and their descendants
        transfer_categories = session.query(Category).filter(Category.category_type == 2).all()
        transfer_ids = set()
        for cat in transfer_categories:
            transfer_ids.update(db._get_all_descendant_ids(cat.id))

        if transfer_ids:
            # Exclude transfer categories, but include uncategorized (None) transactions
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


def _get_category_type(db, category_id):
    """Get category type for a category ID."""
    if category_id is None:
        return None
    cat = db.get_category(category_id)
    return cat.category_type if cat else None


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
@click.option("--this-month", is_flag=True, help="Filter to current month")
@click.option("--this-year", is_flag=True, help="Filter to current year")
@click.option("--this-week", is_flag=True, help="Filter to current week")
@click.option("--last-month", is_flag=True, help="Filter to previous month")
@click.option("--last-year", is_flag=True, help="Filter to previous year")
@click.option("--last-week", is_flag=True, help="Filter to previous week")
@click.option("--category", help="Category path (e.g., 'Food & Dining > Groceries')")
@click.option("--include-transfers", is_flag=True, help="Include transactions with Transfer category")
@click.option("--expand", is_flag=True, help="Expand entire category tree with subtotals")
@click.pass_context
def summary(
    ctx,
    start_date: str,
    end_date: str,
    this_month: bool,
    this_year: bool,
    this_week: bool,
    last_month: bool,
    last_year: bool,
    last_week: bool,
    category: str,
    include_transfers: bool,
    expand: bool,
):
    """Show category summary."""
    db = ctx.obj["db"]
    service = TransactionService(db)

    # Validate period options
    period_options = [this_month, this_year, this_week, last_month, last_year, last_week]
    period_count = sum(period_options)

    if period_count > 1:
        click.echo("Error: Only one period option (--this-month, --this-year, --this-week, --last-month, --last-year, --last-week) can be specified at a time.", err=True)
        ctx.exit(1)

    if period_count > 0 and (start_date or end_date):
        click.echo("Error: Period options (--this-month, --this-year, etc.) cannot be combined with --start-date or --end-date.", err=True)
        ctx.exit(1)

    # Parse dates
    start = None
    end = None

    if period_count == 1:
        # Determine which period option was set
        if this_month:
            start, end = get_date_range("this-month")
        elif this_year:
            start, end = get_date_range("this-year")
        elif this_week:
            start, end = get_date_range("this-week")
        elif last_month:
            start, end = get_date_range("last-month")
        elif last_year:
            start, end = get_date_range("last-year")
        elif last_week:
            start, end = get_date_range("last-week")
    else:
        # Use explicit start/end dates if provided
        if start_date:
            try:
                start = parse_date(start_date)
            except ValueError as e:
                click.echo(f"Error: Invalid start date: {e}", err=True)
                ctx.exit(1)

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
                        "category_type": cat.category_type,
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

        # Group category tree by type: Income (1), Transfer (2), Expense (0)
        income_tree = []
        transfer_tree = []
        expense_tree = []
        uncategorized_total = 0.0

        if category_tree:
            for cat in category_tree:
                # Use category_type from tree if available, otherwise look it up
                cat_type = cat.get("category_type")
                if cat_type is None:
                    cat_type = _get_category_type(db, cat["id"])
                if cat_type == 1:  # Income
                    income_tree.append(cat)
                elif cat_type == 2 and include_transfers:  # Transfer (only if including transfers)
                    transfer_tree.append(cat)
                else:  # Expense (0) or None
                    expense_tree.append(cat)

        # Calculate subtotals
        income_subtotal = 0.0
        transfer_subtotal = 0.0
        expense_subtotal = 0.0

        # Display Income categories first
        if income_tree:
            click.echo("Income")
            click.echo("*" * 80)
            for cat in income_tree:
                total = _calculate_category_total(db, cat["id"], filtered_transactions)
                income_subtotal += total
            _display_expanded_summary(db, income_tree, filtered_transactions, indent=1, is_first=True)
            if income_subtotal != 0:
                click.echo("-" * 80)
                income_subtotal_str = f"${income_subtotal:,.2f}"
                click.echo(f"{'Income Subtotal':<50} {income_subtotal_str:>20}")
                click.echo("=" * 80)
                click.echo()

        # Display Transfer categories (only if including transfers)
        if transfer_tree:
            click.echo("Transfer")
            click.echo("*" * 80)
            for cat in transfer_tree:
                total = _calculate_category_total(db, cat["id"], filtered_transactions)
                transfer_subtotal += total
            _display_expanded_summary(db, transfer_tree, filtered_transactions, indent=1, is_first=True)
            if transfer_subtotal != 0:
                click.echo("-" * 80)
                transfer_subtotal_str = f"${transfer_subtotal:,.2f}"
                click.echo(f"{'Transfer Subtotal':<50} {transfer_subtotal_str:>20}")
                click.echo("=" * 80)
                click.echo()

        # Display Expense categories
        if expense_tree or has_uncategorized:
            click.echo("Expense")
            click.echo("*" * 80)
        if expense_tree:
            for cat in expense_tree:
                total = _calculate_category_total(db, cat["id"], filtered_transactions)
                expense_subtotal += total
            _display_expanded_summary(db, expense_tree, filtered_transactions, indent=1, is_first=True)

        # Display uncategorized if present (treated as Expense)
        if has_uncategorized:
            uncategorized_total = _calculate_category_total(db, None, filtered_transactions)
            expense_subtotal += uncategorized_total
            if uncategorized_total != 0:
                total_str = f"${uncategorized_total:,.2f}"
                click.echo(f"    {'Uncategorized':<46} {total_str:>20}")

        # Show Expense subtotal if there are expense categories or uncategorized
        if expense_tree or has_uncategorized:
            click.echo("-" * 80)
            expense_subtotal_str = f"${expense_subtotal:,.2f}"
            click.echo(f"{'Expense Subtotal':<50} {expense_subtotal_str:>20}")
            click.echo("=" * 80)
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

        # Group summaries by category type: Income (1), Transfer (2), Expense (0)
        # Uncategorized (None) will be treated as Expense type
        income_summaries = []
        transfer_summaries = []
        expense_summaries = []

        for s in summaries:
            total = s["expenses"] + s["income"]  # Net total
            # Skip categories with no transactions
            if total == 0:
                continue

            cat_type = s.get("category_type")
            if cat_type == 1:  # Income
                income_summaries.append(s)
            elif cat_type == 2 and include_transfers:  # Transfer (only if including transfers)
                transfer_summaries.append(s)
            else:  # Expense (0) or Uncategorized (None)
                expense_summaries.append(s)

        # Sort each group by absolute value (descending), then by name for ties
        income_summaries.sort(key=lambda x: (-abs(x["expenses"] + x["income"]), x["category_name"] or ""))
        transfer_summaries.sort(key=lambda x: (-abs(x["expenses"] + x["income"]), x["category_name"] or ""))
        expense_summaries.sort(key=lambda x: (-abs(x["expenses"] + x["income"]), x["category_name"] or ""))

        # Display Income categories first
        if income_summaries:
            click.echo("Income")
            click.echo("*" * 80)
        income_subtotal = 0.0
        for s in income_summaries:
            total = s["expenses"] + s["income"]
            income_subtotal += total
            category_name = s["category_name"] or "Uncategorized"
            total_str = f"${total:,.2f}"
            click.echo(f"    {category_name:<46} {total_str:>20}")

        # Show Income subtotal if there are income categories
        if income_summaries:
            click.echo("-" * 80)
            income_subtotal_str = f"${income_subtotal:,.2f}"
            click.echo(f"{'Income Subtotal':<50} {income_subtotal_str:>20}")
            click.echo("=" * 80)
            click.echo()

        # Display Transfer categories (only if including transfers)
        if transfer_summaries:
            click.echo("Transfer")
            click.echo("*" * 80)
        transfer_subtotal = 0.0
        for s in transfer_summaries:
            total = s["expenses"] + s["income"]
            transfer_subtotal += total
            category_name = s["category_name"] or "Uncategorized"
            total_str = f"${total:,.2f}"
            click.echo(f"    {category_name:<46} {total_str:>20}")

        # Show Transfer subtotal if there are transfer categories
        if transfer_summaries:
            click.echo("-" * 80)
            transfer_subtotal_str = f"${transfer_subtotal:,.2f}"
            click.echo(f"{'Transfer Subtotal':<50} {transfer_subtotal_str:>20}")
            click.echo("=" * 80)
            click.echo()

        # Display Expense categories
        if expense_summaries:
            click.echo("Expense")
            click.echo("*" * 80)
        expense_subtotal = 0.0
        for s in expense_summaries:
            total = s["expenses"] + s["income"]
            expense_subtotal += total
            category_name = s["category_name"] or "Uncategorized"
            total_str = f"${total:,.2f}"
            click.echo(f"    {category_name:<46} {total_str:>20}")

        # Show Expense subtotal if there are expense categories
        if expense_summaries:
            click.echo("-" * 80)
            expense_subtotal_str = f"${expense_subtotal:,.2f}"
            click.echo(f"{'Expense Subtotal':<50} {expense_subtotal_str:>20}")
            click.echo("=" * 80)
        else:
            # If no expense summaries, still need a separator before TOTAL
            click.echo("-" * 80)

    total_str = f"${overall_total:,.2f}" if overall_total != 0 else "-"
    click.echo(f"{'TOTAL':<50} {total_str:>20}")


def register_commands(cli):
    """Register summary command with main CLI."""
    cli.add_command(summary)

