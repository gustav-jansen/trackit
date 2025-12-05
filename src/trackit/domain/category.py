"""Category domain service."""

from typing import Optional
from trackit.database.base import Database


class CategoryService:
    """Service for managing categories."""

    def __init__(self, db: Database):
        """Initialize category service.

        Args:
            db: Database instance
        """
        self.db = db

    def create_category(self, name: str, parent_path: Optional[str] = None) -> int:
        """Create a category.

        Args:
            name: Category name
            parent_path: Optional parent category path (e.g., "Food & Dining")

        Returns:
            Category ID

        Raises:
            ValueError: If parent category doesn't exist
        """
        parent_id = None
        if parent_path is not None:
            parent = self.db.get_category_by_path(parent_path)
            if parent is None:
                raise ValueError(f"Parent category '{parent_path}' not found")
            parent_id = parent["id"]

        return self.db.create_category(name=name, parent_id=parent_id)

    def get_category(self, category_id: int) -> Optional[dict]:
        """Get category by ID.

        Args:
            category_id: Category ID

        Returns:
            Category dict or None if not found
        """
        return self.db.get_category(category_id)

    def get_category_by_path(self, path: str) -> Optional[dict]:
        """Get category by path.

        Args:
            path: Category path (e.g., "Food & Dining > Groceries")

        Returns:
            Category dict or None if not found
        """
        return self.db.get_category_by_path(path)

    def list_categories(self, parent_id: Optional[int] = None) -> list[dict]:
        """List categories.

        Args:
            parent_id: Optional parent category ID to filter by

        Returns:
            List of category dicts
        """
        return self.db.list_categories(parent_id=parent_id)

    def get_category_tree(self) -> list[dict]:
        """Get full category tree.

        Returns:
            List of root categories with nested children
        """
        return self.db.get_category_tree()

    def format_category_path(self, category_id: int) -> str:
        """Get full path for a category.

        Args:
            category_id: Category ID

        Returns:
            Full category path (e.g., "Food & Dining > Groceries")
        """
        cat = self.get_category(category_id)
        if cat is None:
            return ""

        path_parts = [cat["name"]]
        current_parent_id = cat["parent_id"]

        while current_parent_id is not None:
            parent = self.get_category(current_parent_id)
            if parent is None:
                break
            path_parts.append(parent["name"])
            current_parent_id = parent["parent_id"]

        return " > ".join(reversed(path_parts))

