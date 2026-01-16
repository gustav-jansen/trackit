"""Summary commands."""

import click
from trackit.domain.transaction import TransactionService
from trackit.domain.category import CategoryService
from trackit.utils.date_parser import (
    parse_date,
    get_date_range,
    get_last_six_months_range,
)


def _build_descendant_map(category_tree):
    """Build map of category IDs to descendant ID sets."""
    descendant_map = {}

    def collect_descendants(node):
        descendants = {node["id"]}
        for child in node.get("children", []):
            descendants.update(collect_descendants(child))
        descendant_map[node["id"]] = descendants
        return descendants

    for root in category_tree or []:
        collect_descendants(root)

    return descendant_map


def _build_category_tree(db, category_service, category_path):
    """Build category tree, filtered by category path if provided."""
    if category_path:
        category_obj = db.get_category_by_path(category_path)
        if category_obj:

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
                    "children": child_trees,
                }

            subtree = build_subtree(category_obj.id)
            return [subtree] if subtree else []
        return []

    return category_service.get_category_tree()


def _calculate_category_total(descendant_map, category_id, transactions):
    """Calculate total for a category including all its descendants."""
    if category_id is None:
        # Uncategorized transactions
        return sum(float(txn.amount) for txn in transactions if txn.category_id is None)

    descendant_ids = descendant_map.get(category_id, {category_id})
    return sum(
        float(txn.amount) for txn in transactions if txn.category_id in descendant_ids
    )


def _get_category_type(db, category_id):
    """Get category type for a category ID."""
    if category_id is None:
        return None
    cat = db.get_category(category_id)
    return cat.category_type if cat else None


def _get_filtered_transactions(
    service, start_date, end_date, category_path, include_transfers
):
    """Get filtered transactions matching the summary criteria."""
    return service.get_summary_transactions(
        start_date=start_date,
        end_date=end_date,
        category_path=category_path,
        include_transfers=include_transfers,
    )


def _get_transactions_by_period(transactions, group_by_month):
    """Group transactions by month or year.

    Args:
        transactions: List of transaction entities
        group_by_month: If True, group by month; if False, group by year

    Returns:
        Dict mapping period key (e.g., "2024-01" or "2024") to list of transactions
    """
    from collections import defaultdict

    period_transactions = defaultdict(list)

    for txn in transactions:
        if group_by_month:
            # Format: "YYYY-MM"
            period_key = txn.date.strftime("%Y-%m")
        else:
            # Format: "YYYY"
            period_key = txn.date.strftime("%Y")
        period_transactions[period_key].append(txn)

    return dict(period_transactions)


def _calculate_category_total_for_period(
    descendant_map, category_id, period_transactions
):
    """Calculate total for a category in a specific period.

    Args:
        descendant_map: Map of category IDs to descendant ID sets
        category_id: Category ID (None for uncategorized)
        period_transactions: List of transactions for the period

    Returns:
        Total amount for the category in this period
    """
    if category_id is None:
        # Uncategorized transactions
        return sum(
            float(txn.amount) for txn in period_transactions if txn.category_id is None
        )

    descendant_ids = descendant_map.get(category_id, {category_id})
    return sum(
        float(txn.amount)
        for txn in period_transactions
        if txn.category_id in descendant_ids
    )


def _display_columnar_summary_standard(
    db,
    summaries,
    period_keys,
    period_transactions_map,
    include_transfers,
    descendant_map,
):
    """Display columnar summary for standard view.

    Args:
        db: Database instance
        summaries: List of summary dicts from service.get_summary()
        period_keys: Sorted list of period keys (e.g., ["2024-01", "2024-02"])
        period_transactions_map: Dict mapping period key to list of transactions
        include_transfers: Whether to include transfers
        descendant_map: Map of category IDs to descendant ID sets
    """
    # Column widths
    CATEGORY_WIDTH = 50
    PERIOD_COLUMN_WIDTH = 14  # Enough for single digit millions: -$9,999,999.99

    # Build header
    header = f"{'Category':<{CATEGORY_WIDTH}}"
    for period_key in period_keys:
        header += f"   {period_key:>{PERIOD_COLUMN_WIDTH}}"
    click.echo(header)

    # Separator line
    separator = "-" * CATEGORY_WIDTH
    for _ in period_keys:
        separator += "-" * (PERIOD_COLUMN_WIDTH + 3)
    click.echo(separator)

    # Group summaries by category type
    income_summaries = []
    transfer_summaries = []
    expense_summaries = []

    for s in summaries:
        # Calculate total across all periods for this category
        total = sum(
            _calculate_category_total_for_period(
                descendant_map,
                s.get("category_id"),
                period_transactions_map.get(period_key, []),
            )
            for period_key in period_keys
        )
        if total == 0:
            continue

        cat_type = s.get("category_type")
        if cat_type == 1:  # Income
            income_summaries.append(s)
        elif cat_type == 2 and include_transfers:  # Transfer
            transfer_summaries.append(s)
        else:  # Expense (0) or Uncategorized (None)
            expense_summaries.append(s)

    # Sort each group by absolute value (descending), then by name
    income_summaries.sort(
        key=lambda x: (
            -abs(
                sum(
                    _calculate_category_total_for_period(
                        descendant_map,
                        x.get("category_id"),
                        period_transactions_map.get(period_key, []),
                    )
                    for period_key in period_keys
                )
            ),
            x["category_name"] or "",
        )
    )
    transfer_summaries.sort(
        key=lambda x: (
            -abs(
                sum(
                    _calculate_category_total_for_period(
                        descendant_map,
                        x.get("category_id"),
                        period_transactions_map.get(period_key, []),
                    )
                    for period_key in period_keys
                )
            ),
            x["category_name"] or "",
        )
    )
    expense_summaries.sort(
        key=lambda x: (
            -abs(
                sum(
                    _calculate_category_total_for_period(
                        descendant_map,
                        x.get("category_id"),
                        period_transactions_map.get(period_key, []),
                    )
                    for period_key in period_keys
                )
            ),
            x["category_name"] or "",
        )
    )

    # Display Income categories
    if income_summaries:
        click.echo("Income")
        click.echo(
            "*" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
    income_subtotals = [0.0] * len(period_keys)
    for s in income_summaries:
        category_name = s["category_name"] or "Uncategorized"
        row = f"    {category_name:<{CATEGORY_WIDTH - 4}}"
        category_id = s.get("category_id")
        for i, period_key in enumerate(period_keys):
            period_txns = period_transactions_map.get(period_key, [])
            total = _calculate_category_total_for_period(
                descendant_map, category_id, period_txns
            )
            income_subtotals[i] += total
            if total == 0:
                row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                row += f"   ${total:>13,.2f}"
        click.echo(row)

    # Income subtotal
    if income_summaries:
        click.echo(separator)
        subtotal_row = f"{'Income Subtotal':<{CATEGORY_WIDTH}}"
        for i, period_key in enumerate(period_keys):
            if income_subtotals[i] == 0:
                subtotal_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                subtotal_row += f"   ${income_subtotals[i]:>13,.2f}"
        click.echo(subtotal_row)
        click.echo(
            "=" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
        click.echo()

    # Display Transfer categories
    if transfer_summaries:
        click.echo("Transfer")
        click.echo(
            "*" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
    transfer_subtotals = [0.0] * len(period_keys)
    for s in transfer_summaries:
        category_name = s["category_name"] or "Uncategorized"
        row = f"    {category_name:<{CATEGORY_WIDTH - 4}}"
        category_id = s.get("category_id")
        for i, period_key in enumerate(period_keys):
            period_txns = period_transactions_map.get(period_key, [])
            total = _calculate_category_total_for_period(
                descendant_map, category_id, period_txns
            )
            transfer_subtotals[i] += total
            if total == 0:
                row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                row += f"   ${total:>13,.2f}"
        click.echo(row)

    # Transfer subtotal
    if transfer_summaries:
        click.echo(separator)
        subtotal_row = f"{'Transfer Subtotal':<{CATEGORY_WIDTH}}"
        for i, period_key in enumerate(period_keys):
            if transfer_subtotals[i] == 0:
                subtotal_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                subtotal_row += f"   ${transfer_subtotals[i]:>13,.2f}"
        click.echo(subtotal_row)
        click.echo(
            "=" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
        click.echo()

    # Display Expense categories
    if expense_summaries:
        click.echo("Expense")
        click.echo(
            "*" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
    expense_subtotals = [0.0] * len(period_keys)
    for s in expense_summaries:
        category_name = s["category_name"] or "Uncategorized"
        row = f"    {category_name:<{CATEGORY_WIDTH - 4}}"
        category_id = s.get("category_id")
        for i, period_key in enumerate(period_keys):
            period_txns = period_transactions_map.get(period_key, [])
            total = _calculate_category_total_for_period(
                descendant_map, category_id, period_txns
            )
            expense_subtotals[i] += total
            if total == 0:
                row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                row += f"   ${total:>13,.2f}"
        click.echo(row)

    # Expense subtotal
    if expense_summaries:
        click.echo(separator)
        subtotal_row = f"{'Expense Subtotal':<{CATEGORY_WIDTH}}"
        for i, period_key in enumerate(period_keys):
            if expense_subtotals[i] == 0:
                subtotal_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                subtotal_row += f"   ${expense_subtotals[i]:>13,.2f}"
        click.echo(subtotal_row)
        click.echo(
            "=" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
    else:
        click.echo(separator)

    # Overall total
    overall_totals = [0.0] * len(period_keys)
    for period_key in period_keys:
        period_txns = period_transactions_map.get(period_key, [])
        overall_totals[period_keys.index(period_key)] = sum(
            float(txn.amount) for txn in period_txns
        )

    total_row = f"{'TOTAL':<{CATEGORY_WIDTH}}"
    for i, period_key in enumerate(period_keys):
        if overall_totals[i] == 0:
            total_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
        else:
            total_row += f"   ${overall_totals[i]:>13,.2f}"
    click.echo(total_row)


def _display_columnar_summary_expanded(
    db,
    category_tree,
    period_keys,
    period_transactions_map,
    include_transfers,
    has_uncategorized,
    descendant_map,
):
    """Display columnar summary for expanded view.

    Args:
        db: Database instance
        category_tree: Category tree structure
        period_keys: Sorted list of period keys
        period_transactions_map: Dict mapping period key to list of transactions
        include_transfers: Whether to include transfers
        has_uncategorized: Whether there are uncategorized transactions
        descendant_map: Map of category IDs to descendant ID sets
    """
    # Column widths
    CATEGORY_WIDTH = 50
    PERIOD_COLUMN_WIDTH = 14  # Enough for single digit millions: -$9,999,999.99
    INDENT_SIZE = 4

    # Build header
    header = f"{'Category':<{CATEGORY_WIDTH}}"
    for period_key in period_keys:
        header += f"   {period_key:>{PERIOD_COLUMN_WIDTH}}"
    click.echo(header)

    # Separator line
    separator = "-" * CATEGORY_WIDTH
    for _ in period_keys:
        separator += "-" * (PERIOD_COLUMN_WIDTH + 3)
    click.echo(separator)

    # Group category tree by type
    income_tree = []
    transfer_tree = []
    expense_tree = []

    if category_tree:
        for cat in category_tree:
            cat_type = cat.get("category_type")
            if cat_type is None:
                cat_type = _get_category_type(db, cat["id"])
            if cat_type == 1:  # Income
                income_tree.append(cat)
            elif cat_type == 2 and include_transfers:  # Transfer
                transfer_tree.append(cat)
            else:  # Expense (0) or None
                expense_tree.append(cat)

    # Display Income categories
    if income_tree:
        click.echo("Income")
        click.echo(
            "*" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
        income_subtotals = [0.0] * len(period_keys)
        _display_columnar_category_tree(
            db,
            income_tree,
            period_keys,
            period_transactions_map,
            descendant_map,
            1,
            income_subtotals,
        )
        if any(st != 0 for st in income_subtotals):
            click.echo(separator)
            subtotal_row = f"{'Income Subtotal':<{CATEGORY_WIDTH}}"
            for i, period_key in enumerate(period_keys):
                if income_subtotals[i] == 0:
                    subtotal_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
                else:
                    subtotal_row += f"   ${income_subtotals[i]:>13,.2f}"
            click.echo(subtotal_row)
            click.echo(
                "=" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
            )
            click.echo()

    # Display Transfer categories
    if transfer_tree:
        click.echo("Transfer")
        click.echo(
            "*" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
        transfer_subtotals = [0.0] * len(period_keys)
        _display_columnar_category_tree(
            db,
            transfer_tree,
            period_keys,
            period_transactions_map,
            descendant_map,
            1,
            transfer_subtotals,
        )
        if any(st != 0 for st in transfer_subtotals):
            click.echo(separator)
            subtotal_row = f"{'Transfer Subtotal':<{CATEGORY_WIDTH}}"
            for i, period_key in enumerate(period_keys):
                if transfer_subtotals[i] == 0:
                    subtotal_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
                else:
                    subtotal_row += f"   ${transfer_subtotals[i]:>13,.2f}"
            click.echo(subtotal_row)
            click.echo(
                "=" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
            )
            click.echo()

    # Display Expense categories
    if expense_tree or has_uncategorized:
        click.echo("Expense")
        click.echo(
            "*" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
    expense_subtotals = [0.0] * len(period_keys)
    if expense_tree:
        _display_columnar_category_tree(
            db,
            expense_tree,
            period_keys,
            period_transactions_map,
            descendant_map,
            1,
            expense_subtotals,
        )

    # Display uncategorized if present
    if has_uncategorized:
        indent_str = " " * INDENT_SIZE
        category_name = "Uncategorized"
        category_width = CATEGORY_WIDTH - INDENT_SIZE
        row = f"{indent_str}{category_name:<{category_width}}"
        for i, period_key in enumerate(period_keys):
            period_txns = period_transactions_map.get(period_key, [])
            total = _calculate_category_total_for_period(
                descendant_map, None, period_txns
            )
            expense_subtotals[i] += total
            if total == 0:
                row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                row += f"   ${total:>13,.2f}"
        click.echo(row)

    # Expense subtotal
    if expense_tree or has_uncategorized:
        click.echo(separator)
        subtotal_row = f"{'Expense Subtotal':<{CATEGORY_WIDTH}}"
        for i, period_key in enumerate(period_keys):
            if expense_subtotals[i] == 0:
                subtotal_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                subtotal_row += f"   ${expense_subtotals[i]:>13,.2f}"
        click.echo(subtotal_row)
        click.echo(
            "=" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )

    # Overall total
    overall_totals = [0.0] * len(period_keys)
    for period_key in period_keys:
        period_txns = period_transactions_map.get(period_key, [])
        overall_totals[period_keys.index(period_key)] = sum(
            float(txn.amount) for txn in period_txns
        )

    total_row = f"{'TOTAL':<{CATEGORY_WIDTH}}"
    for i, period_key in enumerate(period_keys):
        if overall_totals[i] == 0:
            total_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
        else:
            total_row += f"   ${overall_totals[i]:>13,.2f}"
    click.echo(total_row)


def _display_columnar_category_tree(
    db,
    category_tree,
    period_keys,
    period_transactions_map,
    descendant_map,
    indent=0,
    subtotals=None,
):
    """Recursively display category tree in columnar format.

    Args:
        db: Database instance
        category_tree: List of category dicts with children
        period_keys: Sorted list of period keys
        period_transactions_map: Dict mapping period key to list of transactions
        descendant_map: Map of category IDs to descendant ID sets
        indent: Current indent level
        subtotals: List to accumulate subtotals (modified in place)
    """
    if subtotals is None:
        subtotals = [0.0] * len(period_keys)

    PERIOD_COLUMN_WIDTH = 14  # Enough for single digit millions: -$9,999,999.99
    CATEGORY_WIDTH = 50
    INDENT_SIZE = 4

    # Sort categories by total value (descending), then by name
    def get_sort_key(cat):
        total = sum(
            _calculate_category_total_for_period(
                descendant_map,
                cat["id"],
                period_transactions_map.get(period_key, []),
            )
            for period_key in period_keys
        )
        return (-abs(total), cat["name"])

    sorted_categories = sorted(category_tree, key=get_sort_key)

    for i, cat in enumerate(sorted_categories):
        # Calculate totals for each period
        period_totals = []
        for period_key in period_keys:
            period_txns = period_transactions_map.get(period_key, [])
            total = _calculate_category_total_for_period(
                descendant_map, cat["id"], period_txns
            )
            period_totals.append(total)

        # Skip if all periods are zero
        if all(t == 0 for t in period_totals):
            continue

        # Add blank line before top-level categories (except the first one)
        if indent == 0 and i > 0:
            click.echo()

        indent_str = " " * (INDENT_SIZE * indent)
        category_name = cat["name"]
        category_width = CATEGORY_WIDTH - (INDENT_SIZE * indent)

        row = f"{indent_str}{category_name:<{category_width}}"
        for j, period_key in enumerate(period_keys):
            total = period_totals[j]
            subtotals[j] += total
            if total == 0:
                row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                row += f"   ${total:>13,.2f}"
        click.echo(row)

        # Display children recursively
        if cat.get("children"):
            _display_columnar_category_tree(
                db,
                cat["children"],
                period_keys,
                period_transactions_map,
                descendant_map,
                indent + 1,
                subtotals,
            )


def _display_expanded_summary(
    descendant_map, category_tree, transactions, indent=0, is_first=True
):
    """Recursively display category tree with totals, sorted by value (highest first)."""

    # Sort categories by total value (descending), then by name for ties
    def get_sort_key(cat):
        total = _calculate_category_total(descendant_map, cat["id"], transactions)
        return (-abs(total), cat["name"])  # Negative abs for descending order

    sorted_categories = sorted(category_tree, key=get_sort_key)

    # Use 4 spaces per indent level for larger indentation
    INDENT_SIZE = 4

    for i, cat in enumerate(sorted_categories):
        total = _calculate_category_total(descendant_map, cat["id"], transactions)

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
        click.echo(
            f"{indent_str}{category_name:<{category_width}} {total_str:>{amount_width}}"
        )

        # Display children recursively (they will be sorted in the recursive call)
        if cat.get("children"):
            _display_expanded_summary(
                descendant_map,
                cat["children"],
                transactions,
                indent + 1,
                is_first=False,
            )


@click.command("summary")
@click.option(
    "--start-date",
    help="Start date (YYYY-MM-DD or relative like 'last month', 'this year')",
)
@click.option(
    "--end-date", help="End date (YYYY-MM-DD or relative like 'today', 'this month')"
)
@click.option("--this-month", is_flag=True, help="Filter to current month")
@click.option("--this-year", is_flag=True, help="Filter to current year")
@click.option("--this-week", is_flag=True, help="Filter to current week")
@click.option("--last-month", is_flag=True, help="Filter to previous month")
@click.option("--last-year", is_flag=True, help="Filter to previous year")
@click.option("--last-week", is_flag=True, help="Filter to previous week")
@click.option("--category", help="Category path (e.g., 'Food & Dining > Groceries')")
@click.option(
    "--include-transfers",
    is_flag=True,
    help="Include transactions with Transfer category",
)
@click.option(
    "--expand", is_flag=True, help="Expand entire category tree with subtotals"
)
@click.option(
    "--group-by-month", is_flag=True, help="Group summary by month in columnar format"
)
@click.option(
    "--group-by-year", is_flag=True, help="Group summary by year in columnar format"
)
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
    group_by_month: bool,
    group_by_year: bool,
):
    """Show category summary."""
    db = ctx.obj["db"]
    service = TransactionService(db)

    # Validate period options
    period_options = [
        this_month,
        this_year,
        this_week,
        last_month,
        last_year,
        last_week,
    ]
    period_count = sum(period_options)

    if period_count > 1:
        click.echo(
            "Error: Only one period option (--this-month, --this-year, --this-week, --last-month, --last-year, --last-week) can be specified at a time.",
            err=True,
        )
        ctx.exit(1)

    if period_count > 0 and (start_date or end_date):
        click.echo(
            "Error: Period options (--this-month, --this-year, etc.) cannot be combined with --start-date or --end-date.",
            err=True,
        )
        ctx.exit(1)

    # Validate grouping options
    if group_by_month and group_by_year:
        click.echo(
            "Error: --group-by-month and --group-by-year cannot be specified at the same time.",
            err=True,
        )
        ctx.exit(1)

    # Set default grouping to month if no grouping option specified
    if not group_by_month and not group_by_year:
        group_by_month = True

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

        # If no date filters specified, use default: last 6 months including current month
        if start is None and end is None:
            start, end = get_last_six_months_range()

    # Get filtered transactions for overall total calculation
    filtered_transactions = _get_filtered_transactions(
        service, start, end, category, include_transfers
    )

    if not filtered_transactions:
        click.echo("No transactions found.")
        return

    # Check if grouping is enabled
    if group_by_month or group_by_year:
        # Group transactions by period
        period_transactions_map = _get_transactions_by_period(
            filtered_transactions, group_by_month
        )

        # Get sorted list of period keys (chronologically ascending)
        period_keys = sorted(period_transactions_map.keys())

        if not period_keys:
            click.echo("No transactions found.")
            return

        if expand:
            # Expanded columnar view
            category_service = CategoryService(db)
            category_tree = _build_category_tree(db, category_service, category)
            descendant_map = _build_descendant_map(category_tree)

            has_uncategorized = any(
                txn.category_id is None for txn in filtered_transactions
            )

            click.echo("\nCategory Summary (Expanded):")
            _display_columnar_summary_expanded(
                db,
                category_tree,
                period_keys,
                period_transactions_map,
                include_transfers,
                has_uncategorized,
                descendant_map,
            )
        else:
            # Standard columnar view
            summaries = service.get_summary(
                start_date=start,
                end_date=end,
                category_path=category,
                include_transfers=include_transfers,
            )

            if not summaries:
                click.echo("No transactions found.")
                return

            click.echo("\nCategory Summary:")
            category_service = CategoryService(db)
            category_tree = _build_category_tree(db, category_service, category)
            descendant_map = _build_descendant_map(category_tree)
            _display_columnar_summary_standard(
                db,
                summaries,
                period_keys,
                period_transactions_map,
                include_transfers,
                descendant_map,
            )
        return

    # Calculate overall total from all filtered transactions
    overall_total = sum(float(txn.amount) for txn in filtered_transactions)

    if expand:
        # Expanded view: show full category tree
        category_service = CategoryService(db)
        category_tree = _build_category_tree(db, category_service, category)
        descendant_map = _build_descendant_map(category_tree)

        # Also include uncategorized if there are any
        has_uncategorized = any(
            txn.category_id is None for txn in filtered_transactions
        )

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
                elif (
                    cat_type == 2 and include_transfers
                ):  # Transfer (only if including transfers)
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
                total = _calculate_category_total(
                    descendant_map, cat["id"], filtered_transactions
                )
                income_subtotal += total
            _display_expanded_summary(
                descendant_map,
                income_tree,
                filtered_transactions,
                indent=1,
                is_first=True,
            )
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
                total = _calculate_category_total(
                    descendant_map, cat["id"], filtered_transactions
                )
                transfer_subtotal += total
            _display_expanded_summary(
                descendant_map,
                transfer_tree,
                filtered_transactions,
                indent=1,
                is_first=True,
            )
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
                total = _calculate_category_total(
                    descendant_map, cat["id"], filtered_transactions
                )
                expense_subtotal += total
            _display_expanded_summary(
                descendant_map,
                expense_tree,
                filtered_transactions,
                indent=1,
                is_first=True,
            )

        # Display uncategorized if present (treated as Expense)
        if has_uncategorized:
            uncategorized_total = _calculate_category_total(
                descendant_map, None, filtered_transactions
            )
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
            start_date=start,
            end_date=end,
            category_path=category,
            include_transfers=include_transfers,
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
            elif (
                cat_type == 2 and include_transfers
            ):  # Transfer (only if including transfers)
                transfer_summaries.append(s)
            else:  # Expense (0) or Uncategorized (None)
                expense_summaries.append(s)

        # Sort each group by absolute value (descending), then by name for ties
        income_summaries.sort(
            key=lambda x: (-abs(x["expenses"] + x["income"]), x["category_name"] or "")
        )
        transfer_summaries.sort(
            key=lambda x: (-abs(x["expenses"] + x["income"]), x["category_name"] or "")
        )
        expense_summaries.sort(
            key=lambda x: (-abs(x["expenses"] + x["income"]), x["category_name"] or "")
        )

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
