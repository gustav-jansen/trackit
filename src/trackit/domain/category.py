"""Category domain service."""

from typing import Optional
from trackit.database.base import Database
from trackit.domain.entities import Category as CategoryEntity, CategoryTreeNode
from trackit.domain.errors import category_path_not_found


class CategoryService:
    """Service for managing categories."""

    def __init__(self, db: Database):
        """Initialize category service.

        Args:
            db: Database instance
        """
        self.db = db

    def create_category(
        self,
        name: str,
        parent_path: Optional[str] = None,
        category_type: Optional[int] = None,
    ) -> int:
        """Create a category.

        Args:
            name: Category name
            parent_path: Optional parent category path (e.g., "Food & Dining")
            category_type: Optional category type (0=Expense, 1=Income, 2=Transfer). Defaults to 0 (Expense).

        Returns:
            Category ID

        Raises:
            ValueError: If parent category doesn't exist
        """
        parent_id = None
        if parent_path is not None:
            parent = self.db.get_category_by_path(parent_path)
            if parent is None:
                raise ValueError(category_path_not_found(parent_path))
            parent_id = parent.id

        return self.db.create_category(
            name=name, parent_id=parent_id, category_type=category_type
        )

    def get_category(self, category_id: int) -> Optional[CategoryEntity]:
        """Get category by ID.

        Args:
            category_id: Category ID

        Returns:
            Category entity or None if not found
        """
        return self.db.get_category(category_id)

    def get_category_by_path(self, path: str) -> Optional[CategoryEntity]:
        """Get category by path.

        Args:
            path: Category path (e.g., "Food & Dining > Groceries")

        Returns:
            Category entity or None if not found
        """
        return self.db.get_category_by_path(path)

    def require_category_by_path(self, path: str) -> CategoryEntity:
        """Get category by path or raise if missing.

        Args:
            path: Category path (e.g., "Food & Dining > Groceries")

        Returns:
            Category entity

        Raises:
            ValueError: If category does not exist
        """
        category = self.db.get_category_by_path(path)
        if category is None:
            raise ValueError(category_path_not_found(path))
        return category

    def list_categories(self, parent_id: Optional[int] = None) -> list[CategoryEntity]:
        """List categories.

        Args:
            parent_id: Optional parent category ID to filter by

        Returns:
            List of category entities
        """
        return self.db.list_categories(parent_id=parent_id)

    def get_category_tree(self) -> list[CategoryTreeNode]:
        """Get full category tree.

        Returns:
            List of root categories with nested children
        """
        return self.db.get_category_tree()

    def get_category_subtree_by_path(
        self, category_path: Optional[str]
    ) -> list[CategoryTreeNode]:
        """Get a category subtree by path.

        Args:
            category_path: Category path (e.g., "Food & Dining > Groceries") or None

        Returns:
            List containing the matching subtree root, or the full tree if no path provided.
        """
        if not category_path:
            return self.db.get_category_tree()

        category = self.db.get_category_by_path(category_path)
        if category is None:
            return []

        full_tree = self.db.get_category_tree()

        def find_subtree(
            nodes: list[CategoryTreeNode], category_id: int
        ) -> Optional[CategoryTreeNode]:
            for node in nodes:
                if node.id == category_id:
                    return node
                child_match = find_subtree(list(node.children), category_id)
                if child_match is not None:
                    return child_match
            return None

        subtree = find_subtree(full_tree, category.id)
        return [subtree] if subtree is not None else []

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

        path_parts = [cat.name]
        current_parent_id = cat.parent_id

        while current_parent_id is not None:
            parent = self.get_category(current_parent_id)
            if parent is None:
                break
            path_parts.append(parent.name)
            current_parent_id = parent.parent_id

        return " > ".join(reversed(path_parts))
