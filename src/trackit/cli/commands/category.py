"""Category management commands."""

import click
from trackit.domain.category import CategoryService


def print_category_tree(categories: list[dict], indent: int = 0) -> None:
    """Recursively print category tree."""
    for cat in categories:
        prefix = "  " * indent
        click.echo(f"{prefix}{cat['name']} (ID: {cat['id']})")
        if cat.get("children"):
            print_category_tree(cat["children"], indent + 1)


@click.group()
def category_group():
    """Manage categories."""
    pass


@category_group.command("list")
@click.pass_context
def list_categories(ctx):
    """List all categories in tree format."""
    db = ctx.obj["db"]
    service = CategoryService(db)

    tree = service.get_category_tree()
    if not tree:
        click.echo("No categories found. Run 'init-categories' to create default categories.")
        return

    click.echo("\nCategories:")
    print_category_tree(tree)


@category_group.command("create")
@click.argument("name")
@click.option("--parent", help="Parent category path (e.g., 'Food & Dining')")
@click.option("--type", "category_type", type=click.Choice(["expense", "income", "transfer"], case_sensitive=False), default="expense", help="Category type (default: expense)")
@click.pass_context
def create_category(ctx, name: str, parent: str, category_type: str):
    """Create a new category."""
    db = ctx.obj["db"]
    service = CategoryService(db)

    # Map string values to integers: expense=0, income=1, transfer=2
    type_map = {"expense": 0, "income": 1, "transfer": 2}
    category_type_int = type_map[category_type.lower()]

    try:
        category_id = service.create_category(name=name, parent_path=parent, category_type=category_type_int)
        parent_str = f" under '{parent}'" if parent else ""
        click.echo(f"Created category '{name}'{parent_str} (ID: {category_id})")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


def register_commands(cli):
    """Register category commands with main CLI."""
    cli.add_command(category_group, name="category")

