from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Iterable, TYPE_CHECKING

from .database_utils import get_connection

if TYPE_CHECKING:
    from .article import Article
    from .magazine import Magazine


@dataclass
class Author:
    id: Optional[int]
    _name: str

    # Construction and validation.
    def __init__(self, name: str, id: Optional[int] = None):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Author.name must be a non-empty string")
        self._name = name.strip()
        self.id = id

    # Read-only name property.
    @property
    def name(self) -> str:
        return self._name

    # Database helpers.
    @classmethod
    def new_from_db(cls, row) -> "Author":
    # Accepts a tuple or ``sqlite3.Row``.
        if row is None:
            return None
        if isinstance(row, (list, tuple)):
            id_, name = row
        else:
            id_, name = row["id"], row["name"]
        return cls(name=name, id=id_)

    @classmethod
    def find_by_id(cls, id_: int) -> Optional["Author"]:
        with get_connection() as conn:
            row = conn.execute("SELECT id, name FROM authors WHERE id = ?", (id_,)).fetchone()
            return cls.new_from_db(row)

    # Insert a new row or update the existing row.
    def save(self) -> "Author":
        with get_connection() as conn:
            cur = conn.cursor()
            if self.id is None:
                cur.execute("INSERT INTO authors(name) VALUES (?)", (self._name,))
                self.id = cur.lastrowid
            else:
                cur.execute("UPDATE authors SET name = ? WHERE id = ?", (self._name, self.id))
            conn.commit()
        return self

    # Relationship helpers.
    def articles(self) -> List["Article"]:
        from .article import Article  # Local import to avoid a circular dependency.
        if self.id is None:
            return []
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, content, author_id, magazine_id FROM articles WHERE author_id = ?",
                (self.id,),
            ).fetchall()
            return [Article.new_from_db(r) for r in rows]

    def magazines(self) -> List["Magazine"]:
        from .magazine import Magazine  # Local import to avoid a circular dependency.
        if self.id is None:
            return []
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT m.id, m.name, m.category
                FROM magazines m
                JOIN articles a ON a.magazine_id = m.id
                WHERE a.author_id = ?
                """,
                (self.id,),
            ).fetchall()
            return [Magazine.new_from_db(r) for r in rows]

    # Aggregate helpers.
    def add_article(self, magazine: "Magazine", title: str) -> "Article":
        from .article import Article
        article = Article(title=title, author=self, magazine=magazine)
        return article.save()

    def topic_areas(self) -> List[str]:
        # Unique categories derived from ``magazines()``.
        categories = {m.category for m in self.magazines() if getattr(m, "category", None)}
        return sorted(categories)
