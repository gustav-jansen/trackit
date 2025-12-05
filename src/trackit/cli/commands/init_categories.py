"""Initialize default categories."""

import click
from trackit.domain.category import CategoryService


# Initial category tree structure
INITIAL_CATEGORIES = [
    # Root categories
    ("Income", None),
    ("Food & Dining", None),
    ("Transportation", None),
    ("Shopping", None),
    ("Bills & Utilities", None),
    ("Entertainment", None),
    ("Health & Fitness", None),
    ("Travel", None),
    ("Other", None),
    # Income subcategories
    ("Salary", "Income"),
    ("Investment", "Income"),
    ("Other Income", "Income"),
    # Food & Dining subcategories
    ("Groceries", "Food & Dining"),
    ("Restaurants", "Food & Dining"),
    ("Coffee & Snacks", "Food & Dining"),
    # Transportation subcategories
    ("Gas", "Transportation"),
    ("Public Transit", "Transportation"),
    ("Parking", "Transportation"),
    ("Car Maintenance", "Transportation"),
    # Shopping subcategories
    ("Clothing", "Shopping"),
    ("Electronics", "Shopping"),
    ("Home & Garden", "Shopping"),
    # Bills & Utilities subcategories
    ("Electricity", "Bills & Utilities"),
    ("Water", "Bills & Utilities"),
    ("Internet", "Bills & Utilities"),
    ("Phone", "Bills & Utilities"),
    # Entertainment subcategories
    ("Movies", "Entertainment"),
    ("Music", "Entertainment"),
    ("Sports", "Entertainment"),
    # Health & Fitness subcategories
    ("Gym", "Health & Fitness"),
    ("Pharmacy", "Health & Fitness"),
    ("Doctor", "Health & Fitness"),
    # Travel subcategories
    ("Flights", "Travel"),
    ("Hotels", "Travel"),
    ("Food & Dining", "Travel"),  # Subcategory under Travel
]


@click.command("init-categories")
@click.option("--force", is_flag=True, help="Overwrite existing categories")
@click.pass_context
def init_categories(ctx, force: bool):
    """Initialize database with default category tree."""
    db = ctx.obj["db"]
    service = CategoryService(db)

    # Check if categories already exist
    existing = service.list_categories()
    if existing and not force:
        click.echo("Categories already exist. Use --force to overwrite.")
        return

    click.echo("Creating initial category tree...")

    # Create categories in order: parents first, then children
    # First pass: create root categories
    root_categories = [(name, parent) for name, parent in INITIAL_CATEGORIES if parent is None]
    # Second pass: create child categories
    child_categories = [(name, parent) for name, parent in INITIAL_CATEGORIES if parent is not None]

    created = 0
    errors = 0

    # Create root categories first
    for category_name, parent_name in root_categories:
        try:
            service.create_category(name=category_name, parent_path=None)
            created += 1
        except ValueError as e:
            click.echo(f"Warning: Could not create category '{category_name}': {e}", err=True)
            errors += 1

    # Then create child categories
    for category_name, parent_name in child_categories:
        try:
            service.create_category(name=category_name, parent_path=parent_name)
            created += 1
        except ValueError as e:
            click.echo(f"Warning: Could not create category '{category_name}': {e}", err=True)
            errors += 1

    if errors == 0:
        click.echo(f"Successfully created {created} categories.")
    else:
        click.echo(f"Created {created} categories with {errors} errors.")


def register_commands(cli):
    """Register init-categories command with main CLI."""
    cli.add_command(init_categories)

