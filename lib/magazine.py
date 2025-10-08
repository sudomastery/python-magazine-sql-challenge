from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

from .database_utils import get_connection

if TYPE_CHECKING:
    from .author import Author
    from .article import Article


@dataclass
class Magazine:
    id: Optional[int]
    _name: str
    _category: Optional[str] = None

    def __init__(self, name: str, category: Optional[str] = None, id: Optional[int] = None):
        # Use property setters for validation.
        self.name = name
        self.category = category
        self.id = id

    # Name (read/write with validation).
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Magazine.name must be a non-empty string")
        self._name = value.strip()

    # Category (read/write with validation).
    @property
    def category(self) -> Optional[str]:
        return self._category

    @category.setter
    def category(self, value: Optional[str]) -> None:
        if value is None:
            self._category = None
            return
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Magazine.category must be None or a non-empty string")
        self._category = value.strip()

    # Database helpers.
    @classmethod
    def new_from_db(cls, row) -> "Magazine":
        if row is None:
            return None
        if isinstance(row, (list, tuple)):
            id_, name, category = row
        else:
            id_, name, category = row["id"], row["name"], row["category"]
        return cls(name=name, category=category, id=id_)

    @classmethod
    def find_by_id(cls, id_: int) -> Optional["Magazine"]:
        with get_connection() as conn:
            row = conn.execute("SELECT id, name, category FROM magazines WHERE id = ?", (id_,)).fetchone()
            return cls.new_from_db(row)

    def save(self) -> "Magazine":
        with get_connection() as conn:
            cur = conn.cursor()
            if self.id is None:
                cur.execute(
                    "INSERT INTO magazines(name, category) VALUES (?, ?)",
                    (self._name, self._category),
                )
                self.id = cur.lastrowid
            else:
                cur.execute(
                    "UPDATE magazines SET name = ?, category = ? WHERE id = ?",
                    (self._name, self._category, self.id),
                )
            conn.commit()
        return self

    # Relationship helpers.
    def articles(self) -> List["Article"]:
        from .article import Article
        if self.id is None:
            return []
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, content, author_id, magazine_id FROM articles WHERE magazine_id = ?",
                (self.id,),
            ).fetchall()
            return [Article.new_from_db(r) for r in rows]

    def contributors(self) -> List["Author"]:
        from .author import Author
        if self.id is None:
            return []
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT au.id, au.name
                FROM authors au
                JOIN articles a ON a.author_id = au.id
                WHERE a.magazine_id = ?
                """,
                (self.id,),
            ).fetchall()
            return [Author.new_from_db(r) for r in rows]

    # Aggregate helpers.
    def article_titles(self) -> List[str]:
        if self.id is None:
            return []
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT title FROM articles WHERE magazine_id = ? ORDER BY id",
                (self.id,),
            ).fetchall()
            return [r["title"] if not isinstance(r, (list, tuple)) else r[0] for r in rows]

    @classmethod
    def contributing_authors(cls, magazine_id: int) -> List[int]:
        # Return author IDs with more than two articles in the given magazine.
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT author_id
                FROM articles
                WHERE magazine_id = ?
                GROUP BY author_id
                HAVING COUNT(id) > 2
                """,
                (magazine_id,),
            ).fetchall()
            # rows of single column
            return [r[0] if isinstance(r, (list, tuple)) else r["author_id"] for r in rows]

    @classmethod
    def top_publisher(cls) -> Optional[int]:
        # Return the magazine_id with the most articles, or ``None`` if no data exists.
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT magazine_id, COUNT(id) AS c
                FROM articles
                GROUP BY magazine_id
                ORDER BY c DESC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            return row[0] if isinstance(row, (list, tuple)) else row["magazine_id"]
