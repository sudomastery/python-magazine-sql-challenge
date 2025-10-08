from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from .database_utils import get_connection

if TYPE_CHECKING:
    from .author import Author
    from .magazine import Magazine


@dataclass
class Article:
    id: Optional[int]
    _title: str
    _author: "Author"
    _magazine: "Magazine"
    content: Optional[str] = None

    def __init__(
        self,
        title: str,
        author: "Author",
        magazine: "Magazine",
        content: Optional[str] = None,
        id: Optional[int] = None,
    ) -> None:
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Article.title must be a non-empty string")
        self._title = title.strip()
        # Use property setters for validation and assignment.
        self.author = author
        self.magazine = magazine
        self.content = content
        self.id = id

    # Title (read-only).
    @property
    def title(self) -> str:
        return self._title

    # Author object reference.
    @property
    def author(self) -> "Author":
        return self._author

    @author.setter
    def author(self, value: "Author") -> None:
        from .author import Author
        if not isinstance(value, Author) or value is None:
            raise ValueError("Article.author must be an Author instance")
        self._author = value

    # Magazine object reference.
    @property
    def magazine(self) -> "Magazine":
        return self._magazine

    @magazine.setter
    def magazine(self, value: "Magazine") -> None:
        from .magazine import Magazine
        if not isinstance(value, Magazine) or value is None:
            raise ValueError("Article.magazine must be a Magazine instance")
        self._magazine = value

    # Database helpers.
    @classmethod
    def new_from_db(cls, row) -> "Article":
        if row is None:
            return None
        if isinstance(row, (list, tuple)):
            id_, title, content, author_id, magazine_id = row
        else:
            id_, title, content, author_id, magazine_id = (
                row["id"], row["title"], row["content"], row["author_id"], row["magazine_id"],
            )
        # Hydrate related objects using their identifiers.
        from .author import Author
        from .magazine import Magazine
        author = Author.find_by_id(author_id)
        magazine = Magazine.find_by_id(magazine_id)
        return cls(title=title, content=content, author=author, magazine=magazine, id=id_)

    @classmethod
    def find_by_id(cls, id_: int) -> Optional["Article"]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, title, content, author_id, magazine_id FROM articles WHERE id = ?",
                (id_,),
            ).fetchone()
            return cls.new_from_db(row)

    def save(self) -> "Article":
        # Ensure related objects are saved and have identifiers.
        if getattr(self.author, "id", None) is None:
            self.author.save()
        if getattr(self.magazine, "id", None) is None:
            self.magazine.save()
        with get_connection() as conn:
            cur = conn.cursor()
            if self.id is None:
                cur.execute(
                    "INSERT INTO articles(title, content, author_id, magazine_id) VALUES (?, ?, ?, ?)",
                    (self._title, self.content, self.author.id, self.magazine.id),
                )
                self.id = cur.lastrowid
            else:
                cur.execute(
                    "UPDATE articles SET title = ?, content = ?, author_id = ?, magazine_id = ? WHERE id = ?",
                    (self._title, self.content, self.author.id, self.magazine.id, self.id),
                )
            conn.commit()
        return self
